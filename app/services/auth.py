from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import sqlite3
from typing import List, Optional

from app.core.database import get_db
from app.core.errors import KioskException
from app.core.security import verify_password, decode_access_token
from app.repositories.user import UserRepository

# OAuth2 scheme config. Auto_error is False so we can raise custom KioskException.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

class AuthService:
    @staticmethod
    def authenticate_user(db: sqlite3.Connection, username: str, password: str) -> dict:
        """
        Authenticates a user by checking their username and password hash.
        Raises KioskException if authentication fails.
        """
        user = UserRepository.get_by_username(db, username)
        if not user:
            raise KioskException(
                code="UNAUTHORIZED",
                message="Usuario o contraseña incorrectos",
                status_code=401
            )
            
        if not verify_password(password, user["password_hash"]):
            raise KioskException(
                code="UNAUTHORIZED",
                message="Usuario o contraseña incorrectos",
                status_code=401
            )
            
        if user["activo"] != 1:
            raise KioskException(
                code="USER_INACTIVE",
                message="El usuario está inactivo y no puede iniciar sesión",
                status_code=401
            )
            
        return user

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: sqlite3.Connection = Depends(get_db)
) -> dict:
    """
    FastAPI dependency to retrieve the current authenticated user.
    Validates token and user activity.
    """
    if not token:
        raise KioskException(
            code="UNAUTHORIZED",
            message="No se proporcionaron credenciales de autenticación",
            status_code=401
        )
    
    payload = decode_access_token(token)
    if not payload:
        raise KioskException(
            code="INVALID_TOKEN",
            message="Token de autenticación inválido o expirado",
            status_code=401
        )
    
    username = payload.get("sub") or payload.get("username")
    if not username:
        raise KioskException(
            code="INVALID_TOKEN",
            message="Token de autenticación no contiene información del sujeto",
            status_code=401
        )
    
    user = UserRepository.get_by_username(db, username)
    if not user:
        raise KioskException(
            code="USER_NOT_FOUND",
            message="El usuario del token no existe en el sistema",
            status_code=401
        )
    
    if user["activo"] != 1:
        raise KioskException(
            code="USER_INACTIVE",
            message="El usuario está inactivo y tiene denegado el acceso",
            status_code=401
        )
        
    return user

class RoleChecker:
    """
    FastAPI dependency builder to enforce role-based access control (RBAC).
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["rol"] not in self.allowed_roles:
            raise KioskException(
                code="FORBIDDEN",
                message=f"No tiene permisos para realizar esta acción. Roles permitidos: {', '.join(self.allowed_roles)}",
                status_code=403
            )
        return current_user
