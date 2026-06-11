import os
import sys
import uuid
from datetime import datetime, timezone
import bcrypt

# Add project root to sys.path to allow absolute imports of app
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.core.database import get_db_conn
from app.core.security import hash_password

def create_user_cli():
    print("=== Creador de Usuarios del Kiosco (CLI) ===")
    
    nombre = input("Ingrese el Nombre Completo (ej: Juan Pérez): ").strip()
    if not nombre:
        print("Error: El nombre es obligatorio.")
        return
        
    username = input("Ingrese el Nombre de Usuario (username): ").strip().lower()
    if not username:
        print("Error: El nombre de usuario es obligatorio.")
        return
        
    password = input("Ingrese la Contraseña: ").strip()
    if len(password) < 4:
        print("Error: La contraseña debe tener al menos 4 caracteres.")
        return
        
    print("\nRoles disponibles:")
    print("1. CAJERO")
    print("2. SUPERVISOR")
    print("3. ADMINISTRADOR")
    rol_choice = input("Seleccione el rol (1, 2, 3) [por defecto 1]: ").strip()
    
    if rol_choice == "2":
        rol = "SUPERVISOR"
    elif rol_choice == "3":
        rol = "ADMINISTRADOR"
    else:
        rol = "CAJERO"

    hashed = hash_password(password)
    user_id = uuid.uuid4().hex
    ahora = datetime.now(timezone.utc).isoformat()

    try:
        with get_db_conn() as conn:
            cursor = conn.cursor()
            
            # Verificar si el nombre de usuario ya existe
            cursor.execute("SELECT id FROM usuarios WHERE username = ?;", (username,))
            if cursor.fetchone():
                print(f"\nError: El nombre de usuario '{username}' ya está registrado.")
                return
                
            cursor.execute(
                """
                INSERT INTO usuarios (id, nombre, username, password_hash, rol, activo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (user_id, nombre, username, hashed, rol, 1, ahora)
            )
            print(f"\n¡Usuario '{username}' ({rol}) creado con éxito!")
            print(f"ID del usuario: {user_id}")
            
    except Exception as e:
        print(f"\nOcurrió un error al crear el usuario en la base de datos: {e}")

if __name__ == "__main__":
    create_user_cli()
