from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum
from typing import Optional

class UserRole(str, Enum):
    ADMINISTRADOR = "ADMINISTRADOR"
    SUPERVISOR = "SUPERVISOR"
    CAJERO = "CAJERO"

class UserBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    username: str = Field(..., min_length=3, max_length=50)
    rol: UserRole
    activo: int = Field(1, ge=0, le=1)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        # Lowercase username to avoid case sensitivity issues
        v = v.strip().lower()
        if not v.isalnum() and "_" not in v and "-" not in v:
            raise ValueError("El nombre de usuario solo debe contener caracteres alfanuméricos, guiones o guiones bajos")
        return v

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)

class UserUpdatePassword(BaseModel):
    password: str = Field(..., min_length=6, max_length=100)

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    username: str
    rol: UserRole
    activo: int
    created_at: str


class UserShort(BaseModel):
    id: str
    nombre: str
    rol: UserRole

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserShort

class TokenData(BaseModel):
    username: Optional[str] = None
    rol: Optional[str] = None
