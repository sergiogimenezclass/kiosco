from fastapi import APIRouter, Depends, status
import sqlite3
from typing import List

from app.core.database import get_db
from app.core.errors import KioskException
from app.core.security import hash_password
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserResponse, UserUpdatePassword
from app.services.auth import get_current_user, RoleChecker

router = APIRouter(tags=["usuarios"])

@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Returns the profile of the currently logged-in user.
    """
    return current_user

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(RoleChecker(["ADMINISTRADOR"]))
) -> dict:
    """
    Creates a new user. Only available to ADMINISTRADOR role.
    """
    # Hash password
    hashed = hash_password(user_in.password)
    # Save in DB
    user = UserRepository.create(db, user_in, hashed)
    return user

@router.patch("/{user_id}/password", status_code=status.HTTP_200_OK)
@router.put("/{user_id}/password", status_code=status.HTTP_200_OK)
def change_password(
    user_id: str,
    password_in: UserUpdatePassword,
    db: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(RoleChecker(["ADMINISTRADOR"]))
) -> dict:
    """
    Updates the password of a user by their ID. Only available to ADMINISTRADOR role.
    """
    # Check if user exists
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise KioskException(
            code="USER_NOT_FOUND",
            message="El usuario especificado no existe",
            status_code=404
        )
    
    # Hash and update
    hashed = hash_password(password_in.password)
    UserRepository.update_password(db, user_id, hashed)
    return {"message": "Contraseña actualizada exitosamente"}

@router.patch("/{user_id}/desactivar", status_code=status.HTTP_200_OK)
@router.put("/{user_id}/desactivar", status_code=status.HTTP_200_OK)
@router.patch("/{user_id}/deactivate", status_code=status.HTTP_200_OK)
@router.put("/{user_id}/deactivate", status_code=status.HTTP_200_OK)
def deactivate_user(
    user_id: str,
    db: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(RoleChecker(["ADMINISTRADOR"]))
) -> dict:
    """
    Deactivates a user (sets active=0). Physical deletion is forbidden.
    Only available to ADMINISTRADOR role. Prevents self-deactivation.
    """
    # Prevent self-deactivation
    if admin_user["id"] == user_id:
        raise KioskException(
            code="SELF_DEACTIVATION_FORBIDDEN",
            message="No puedes desactivar tu propia cuenta de administrador",
            status_code=400
        )
        
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise KioskException(
            code="USER_NOT_FOUND",
            message="El usuario especificado no existe",
            status_code=404
        )
        
    UserRepository.deactivate(db, user_id)
    return {"message": "Usuario desactivado exitosamente"}

@router.get("", response_model=List[UserResponse])
def list_users(
    db: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(RoleChecker(["ADMINISTRADOR", "SUPERVISOR"]))
) -> List[dict]:
    """
    Lists all users. Available to ADMINISTRADOR and SUPERVISOR roles.
    """
    users = UserRepository.get_all(db)
    return users
