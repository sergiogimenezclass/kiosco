from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
import sqlite3

from app.core.database import get_db
from app.core.security import create_access_token
from app.schemas.user import Token, UserResponse
from app.services.auth import AuthService, get_current_user

router = APIRouter(tags=["autenticación"])

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: sqlite3.Connection = Depends(get_db)
) -> dict:
    """
    Log in a user by verifying their credentials.
    Supports form data (application/x-www-form-urlencoded), required by OpenAPI/Swagger.
    Returns a JWT access token and user info.
    """
    user = AuthService.authenticate_user(db, form_data.username, form_data.password)
    
    # Generate access token
    access_token = create_access_token(data={"sub": user["username"], "rol": user["rol"]})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "nombre": user["nombre"],
            "rol": user["rol"]
        }
    }

@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Returns the profile of the currently logged-in user.
    """
    return current_user

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout() -> dict:
    """
    Client-side session invalidation endpoint.
    """
    return {"message": "Sesión cerrada exitosamente"}
