import sqlite3
from typing import List, Optional
from app.core.errors import KioskException
from app.repositories.caja import CajaRepository
from app.schemas.caja import CajaApertura, CajaCierre, MovimientoCajaCreate

class CajaService:
    @staticmethod
    def get_active_caja(db: sqlite3.Connection) -> Optional[dict]:
        """Gets the currently open cash register or None."""
        return CajaRepository.get_active_caja(db)

    @staticmethod
    def get_caja_by_id(db: sqlite3.Connection, caja_id: str) -> dict:
        """Gets a cash register by its ID, raising 404 if not found."""
        caja = CajaRepository.get_by_id(db, caja_id)
        if not caja:
            raise KioskException(
                code="CASH_REGISTER_NOT_FOUND",
                message="La caja especificada no existe",
                status_code=404
            )
        return caja

    @staticmethod
    def apertura(db: sqlite3.Connection, user_id: str, apertura_in: CajaApertura) -> dict:
        """Opens a new cash register after validating that no other register is open."""
        active_caja = CajaRepository.get_active_caja(db)
        if active_caja:
            raise KioskException(
                code="ACTIVE_CASH_REGISTER_EXISTS",
                message="Ya existe una caja abierta en el sistema",
                status_code=400
            )
            
        if apertura_in.monto_inicial_centavos < 0:
            raise KioskException(
                code="INVALID_AMOUNT",
                message="El monto inicial no puede ser negativo",
                status_code=400
            )
            
        return CajaRepository.create_caja(db, user_id, apertura_in.monto_inicial_centavos)

    @staticmethod
    def cierre(db: sqlite3.Connection, user_cierre_id: str, cierre_in: CajaCierre) -> dict:
        """Closes the currently active cash register and calculates discrepancy."""
        active_caja = CajaRepository.get_active_caja(db)
        if not active_caja:
            raise KioskException(
                code="CASH_REGISTER_NOT_FOUND",
                message="No hay ninguna caja abierta activa para cerrar",
                status_code=404
            )
            
        caja_id = active_caja["id"]
        
        # Calculate total cash register inflows and outflows
        ingresos = CajaRepository.get_total_movimientos_by_tipo(db, caja_id, "INGRESO")
        retiros = CajaRepository.get_total_movimientos_by_tipo(db, caja_id, "RETIRO")
        
        # Calculate total cash sales (EFECTIVO)
        # Using raw query so we don't depend on uncreated SalesRepository
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT COALESCE(SUM(total_centavos), 0) 
            FROM ventas 
            WHERE caja_id = ? AND metodo_pago = 'EFECTIVO' AND estado = 'COMPLETADA';
            """,
            (caja_id,)
        )
        ventas_efectivo = cursor.fetchone()[0]
        
        # monto_esperado = monto_inicial + ingresos - retiros + ventas_efectivo
        monto_esperado_centavos = active_caja["monto_inicial_centavos"] + ingresos - retiros + ventas_efectivo
        
        # desviacion = declarado - esperado
        desviacion_centavos = cierre_in.monto_declarado_centavos - monto_esperado_centavos
        
        return CajaRepository.close_caja(
            db, 
            caja_id, 
            user_cierre_id, 
            cierre_in.monto_declarado_centavos, 
            monto_esperado_centavos, 
            desviacion_centavos
        )

    @staticmethod
    def reabrir(db: sqlite3.Connection, caja_id: str) -> dict:
        """Reopens a closed cash register if no other cash register is open."""
        # Check active cash register
        active_caja = CajaRepository.get_active_caja(db)
        if active_caja:
            raise KioskException(
                code="ACTIVE_CASH_REGISTER_EXISTS",
                message="No se puede reabrir la caja porque ya existe otra caja abierta",
                status_code=409
            )
            
        # Check if requested register exists
        caja = CajaService.get_caja_by_id(db, caja_id)
        
        # Check register state
        if caja["estado"] == "ABIERTA":
            raise KioskException(
                code="INVALID_CASH_REGISTER_STATE",
                message="La caja ya se encuentra abierta",
                status_code=400
            )
            
        return CajaRepository.reopen_caja(db, caja_id)

    @staticmethod
    def get_historial(db: sqlite3.Connection) -> List[dict]:
        """Retrieves a historical list of all cash registers."""
        return CajaRepository.get_historial(db)


    # --- MOVIMIENTOS DE CAJA ---

    @staticmethod
    def registrar_movimiento(db: sqlite3.Connection, user_id: str, mov_in: MovimientoCajaCreate) -> dict:
        """Registers a cash register movement (deposit/withdrawal)."""
        active_caja = CajaRepository.get_active_caja(db)
        if not active_caja:
            raise KioskException(
                code="CASH_REGISTER_NOT_FOUND",
                message="No hay ninguna caja abierta activa para registrar movimientos de caja",
                status_code=404
            )
            
        if mov_in.monto_centavos <= 0:
            raise KioskException(
                code="INVALID_AMOUNT",
                message="El monto del movimiento debe ser mayor a cero centavos",
                status_code=400
            )
            
        return CajaRepository.create_movimiento(
            db, 
            active_caja["id"], 
            user_id, 
            mov_in.tipo.value, 
            mov_in.monto_centavos, 
            mov_in.motivo
        )

    @staticmethod
    def get_movimientos_caja_actual(db: sqlite3.Connection) -> List[dict]:
        """Retrieves all movements associated with the active register."""
        active_caja = CajaRepository.get_active_caja(db)
        if not active_caja:
            raise KioskException(
                code="CASH_REGISTER_NOT_FOUND",
                message="No hay ninguna caja abierta activa en este momento",
                status_code=404
            )
        return CajaRepository.get_movimientos_by_caja_id(db, active_caja["id"])

    @staticmethod
    def get_all_movimientos(db: sqlite3.Connection) -> List[dict]:
        """Retrieves all movements (useful for supervisor/admin auditing)."""
        return CajaRepository.get_all_movimientos(db)
