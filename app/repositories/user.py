import sqlite3
import uuid
import datetime
from typing import Optional, List
from app.core.errors import KioskException
from app.schemas.user import UserCreate

class UserRepository:
    @staticmethod
    def get_by_id(conn: sqlite3.Connection, user_id: str) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, username, password_hash, rol, activo, created_at FROM usuarios WHERE id = ?;", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_by_username(conn: sqlite3.Connection, username: str) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, username, password_hash, rol, activo, created_at FROM usuarios WHERE username = ?;", (username.strip().lower(),))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def create(conn: sqlite3.Connection, user_create: UserCreate, hashed_password: str) -> dict:
        cursor = conn.cursor()
        user_id = uuid.uuid4().hex
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        try:
            cursor.execute(
                """
                INSERT INTO usuarios (id, nombre, username, password_hash, rol, activo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    user_id,
                    user_create.nombre,
                    user_create.username.strip().lower(),
                    hashed_password,
                    user_create.rol,
                    user_create.activo,
                    created_at
                )
            )
            return {
                "id": user_id,
                "nombre": user_create.nombre,
                "username": user_create.username.strip().lower(),
                "rol": user_create.rol,
                "activo": user_create.activo,
                "created_at": created_at
            }
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e) or "username" in str(e):
                raise KioskException(
                    code="USERNAME_ALREADY_EXISTS",
                    message=f"El nombre de usuario '{user_create.username}' ya está registrado",
                    status_code=409
                )
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al guardar el usuario en la base de datos: {str(e)}",
                status_code=500
            )

    @staticmethod
    def update_password(conn: sqlite3.Connection, user_id: str, hashed_password: str) -> bool:
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?;", (hashed_password, user_id))
        return cursor.rowcount > 0

    @staticmethod
    def deactivate(conn: sqlite3.Connection, user_id: str) -> bool:
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET activo = 0 WHERE id = ?;", (user_id,))
        return cursor.rowcount > 0

    @staticmethod
    def get_all(conn: sqlite3.Connection) -> List[dict]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, username, rol, activo, created_at FROM usuarios;")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
