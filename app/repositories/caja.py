import sqlite3
import uuid
import datetime
from typing import List, Optional
from app.core.errors import KioskException

class CajaRepository:
    @staticmethod
    def get_active_caja(conn: sqlite3.Connection) -> Optional[dict]:
        """
        Retrieves the active (open) cash register if any.
        There can only be one active register due to database-level index.
        """
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, usuario_apertura_id, usuario_cierre_id, estado, 
                   monto_inicial_centavos, monto_declarado_centavos, 
                   monto_esperado_centavos, desviacion_centavos, 
                   fecha_apertura, fecha_cierre 
            FROM cajas 
            WHERE estado = 'ABIERTA';
            """
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_by_id(conn: sqlite3.Connection, caja_id: str) -> Optional[dict]:
        """Retrieves a specific cash register by ID."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, usuario_apertura_id, usuario_cierre_id, estado, 
                   monto_inicial_centavos, monto_declarado_centavos, 
                   monto_esperado_centavos, desviacion_centavos, 
                   fecha_apertura, fecha_cierre 
            FROM cajas 
            WHERE id = ?;
            """,
            (caja_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def create_caja(conn: sqlite3.Connection, user_apertura_id: str, monto_inicial_centavos: int) -> dict:
        """Creates a new cash register in the open state."""
        cursor = conn.cursor()
        caja_id = uuid.uuid4().hex
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        try:
            cursor.execute(
                """
                INSERT INTO cajas (
                    id, usuario_apertura_id, estado, monto_inicial_centavos, fecha_apertura
                ) VALUES (?, ?, 'ABIERTA', ?, ?);
                """,
                (caja_id, user_apertura_id, monto_inicial_centavos, now_str)
            )
            return {
                "id": caja_id,
                "usuario_apertura_id": user_apertura_id,
                "usuario_cierre_id": None,
                "estado": "ABIERTA",
                "monto_inicial_centavos": monto_inicial_centavos,
                "monto_declarado_centavos": None,
                "monto_esperado_centavos": None,
                "desviacion_centavos": None,
                "fecha_apertura": now_str,
                "fecha_cierre": None
            }
        except sqlite3.IntegrityError as e:
            if "unica_caja_abierta" in str(e) or "UNIQUE" in str(e):
                raise KioskException(
                    code="ACTIVE_CASH_REGISTER_EXISTS",
                    message="Ya existe una caja abierta en el sistema",
                    status_code=409
                )
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al abrir la caja: {str(e)}",
                status_code=500
            )

    @staticmethod
    def close_caja(
        conn: sqlite3.Connection, 
        caja_id: str, 
        user_cierre_id: str, 
        monto_declarado_centavos: int, 
        monto_esperado_centavos: int, 
        desviacion_centavos: int
    ) -> dict:
        """Closes an active cash register and saves the blind closing calculations."""
        cursor = conn.cursor()
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        try:
            cursor.execute(
                """
                UPDATE cajas 
                SET usuario_cierre_id = ?, 
                    estado = 'CERRADA', 
                    monto_declarado_centavos = ?, 
                    monto_esperado_centavos = ?, 
                    desviacion_centavos = ?, 
                    fecha_cierre = ? 
                WHERE id = ?;
                """,
                (user_cierre_id, monto_declarado_centavos, monto_esperado_centavos, desviacion_centavos, now_str, caja_id)
            )
            if cursor.rowcount == 0:
                raise KioskException(
                    code="CASH_REGISTER_NOT_FOUND",
                    message="No se encontró la caja especificada",
                    status_code=404
                )
            
            return CajaRepository.get_by_id(conn, caja_id)
        except sqlite3.IntegrityError as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al cerrar la caja: {str(e)}",
                status_code=500
            )

    @staticmethod
    def reopen_caja(conn: sqlite3.Connection, caja_id: str) -> dict:
        """Reopens a closed cash register (clears closing data)."""
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                UPDATE cajas 
                SET usuario_cierre_id = NULL, 
                    estado = 'ABIERTA', 
                    monto_declarado_centavos = NULL, 
                    monto_esperado_centavos = NULL, 
                    desviacion_centavos = NULL, 
                    fecha_cierre = NULL 
                WHERE id = ?;
                """,
                (caja_id,)
            )
            if cursor.rowcount == 0:
                raise KioskException(
                    code="CASH_REGISTER_NOT_FOUND",
                    message="No se encontró la caja especificada",
                    status_code=404
                )
            
            return CajaRepository.get_by_id(conn, caja_id)
        except sqlite3.IntegrityError as e:
            if "unica_caja_abierta" in str(e) or "UNIQUE" in str(e):
                raise KioskException(
                    code="ACTIVE_CASH_REGISTER_EXISTS",
                    message="No se puede reabrir la caja porque ya hay otra caja abierta activa en el sistema",
                    status_code=409
                )
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al reabrir la caja: {str(e)}",
                status_code=500
            )

    @staticmethod
    def get_historial(conn: sqlite3.Connection) -> List[dict]:
        """Lists all cash registers in reverse chronological order."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, usuario_apertura_id, usuario_cierre_id, estado, 
                   monto_inicial_centavos, monto_declarado_centavos, 
                   monto_esperado_centavos, desviacion_centavos, 
                   fecha_apertura, fecha_cierre 
            FROM cajas 
            ORDER BY fecha_apertura DESC;
            """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


    # --- MOVIMIENTOS DE CAJA ---

    @staticmethod
    def create_movimiento(
        conn: sqlite3.Connection, 
        caja_id: str, 
        usuario_id: str, 
        tipo: str, 
        monto_centavos: int, 
        motivo: str
    ) -> dict:
        """Creates a cash register movement (deposit/withdrawal)."""
        cursor = conn.cursor()
        mov_id = uuid.uuid4().hex
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        try:
            cursor.execute(
                """
                INSERT INTO movimientos_caja (
                    id, caja_id, usuario_id, tipo, monto_centavos, motivo, fecha
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (mov_id, caja_id, usuario_id, tipo, monto_centavos, motivo.strip(), now_str)
            )
            return {
                "id": mov_id,
                "caja_id": caja_id,
                "usuario_id": usuario_id,
                "tipo": tipo,
                "monto_centavos": monto_centavos,
                "motivo": motivo.strip(),
                "fecha": now_str
            }
        except sqlite3.IntegrityError as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al registrar el movimiento de caja: {str(e)}",
                status_code=500
            )

    @staticmethod
    def get_movimientos_by_caja_id(conn: sqlite3.Connection, caja_id: str) -> List[dict]:
        """Retrieves all movements associated with a specific cash register."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, caja_id, usuario_id, tipo, monto_centavos, motivo, fecha 
            FROM movimientos_caja 
            WHERE caja_id = ? 
            ORDER BY fecha ASC;
            """,
            (caja_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_total_movimientos_by_tipo(conn: sqlite3.Connection, caja_id: str, tipo: str) -> int:
        """Returns the sum of all movements of a specific type (INGRESO or RETIRO) for a cash register."""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT SUM(monto_centavos) FROM movimientos_caja WHERE caja_id = ? AND tipo = ?;",
            (caja_id, tipo)
        )
        val = cursor.fetchone()[0]
        return val if val is not None else 0

    @staticmethod
    def get_all_movimientos(conn: sqlite3.Connection) -> List[dict]:
        """Retrieves all movements across all cash registers, ordered by date desc."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, caja_id, usuario_id, tipo, monto_centavos, motivo, fecha 
            FROM movimientos_caja 
            ORDER BY fecha DESC;
            """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
