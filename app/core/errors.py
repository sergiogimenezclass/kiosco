from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Dict, Any, Optional

class KioskException(Exception):
    """Base exception for application errors."""
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

# Standardized Exception Handlers for FastAPI

async def kiosk_exception_handler(request: Request, exc: KioskException) -> JSONResponse:
    """Handles custom KioskException and returns the standard error response format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles FastAPI RequestValidationError and returns the standard error response format."""
    details = {}
    for error in exc.errors():
        # Format the field location nicely (e.g. body -> items -> 0 -> quantity)
        loc = ".".join(str(l) for l in error.get("loc", []))
        details[loc] = error.get("msg", "Validation error")
        
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Los datos proporcionados no son válidos",
                "details": details
            }
        }
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches all unhandled exceptions and formats them as standard internal server error."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Ha ocurrido un error inesperado en el servidor",
                "details": {"exception": str(exc)}
            }
        }
    )
