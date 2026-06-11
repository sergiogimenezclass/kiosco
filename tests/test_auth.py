import os
import sys
import pytest
from fastapi.testclient import TestClient
import sqlite3

# Add project root directory to path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment or change configuration before imports
from app.core.config import settings
settings.DB_PATH = "test_kiosco.db"


# Now import the modules
from app.main import app
from app.core.database import init_db, get_db_conn
from app.repositories.user import UserRepository

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    db_file = settings.DB_URL
    # Delete test db if it exists
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except PermissionError:
            pass
            
    # Initialize test database (seeds admin user)
    init_db()
    
    yield
    
    # Cleanup test database file after all tests in this module
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except PermissionError:
            pass

def test_admin_login():
    """
    Test that the seeded default admin user can log in successfully.
    """
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    json_data = response.json()
    assert "access_token" in json_data
    assert json_data["token_type"] == "bearer"

def test_login_failure():
    """
    Test that logging in with incorrect credentials fails with 401.
    """
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"

def test_get_current_user_profile():
    """
    Test getting current user profile with valid, invalid, and missing credentials.
    """
    # 1. No token provided
    response = client.get("/api/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    
    # 2. Invalid token
    response = client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer invalidtoken123"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"
    
    # 3. Valid token
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    token = login_resp.json()["access_token"]
    
    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["rol"] == "ADMINISTRADOR"
    assert data["activo"] == 1
    assert "password_hash" not in data  # Crucial: verify security is respected and hash isn't leaked

def test_user_creation_rbac():
    """
    Test that user creation endpoints enforce Role-Based Access Control (RBAC).
    Admin can create users, Supervisor cannot.
    """
    # Login as admin to get token
    login_admin = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    admin_token = login_admin.json()["access_token"]
    
    # 1. Create a Supervisor user as Admin (Success)
    new_user_data = {
        "nombre": "Juan Supervisor",
        "username": "juansup",
        "password": "superpassword123",
        "rol": "SUPERVISOR",
        "activo": 1
    }
    response = client.post(
        "/api/users",
        json=new_user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    supervisor = response.json()
    assert supervisor["username"] == "juansup"
    assert supervisor["rol"] == "SUPERVISOR"
    assert "id" in supervisor
    
    # Login as the new Supervisor to get a token
    login_sup = client.post(
        "/api/auth/login",
        data={"username": "juansup", "password": "superpassword123"}
    )
    sup_token = login_sup.json()["access_token"]
    
    # 2. Try to create another user as Supervisor (Forbidden)
    response = client.post(
        "/api/users",
        json={
            "nombre": "Pedro Cajero",
            "username": "pedrocaj",
            "password": "cajeropassword123",
            "rol": "CAJERO",
            "activo": 1
        },
        headers={"Authorization": f"Bearer {sup_token}"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

def test_change_password():
    """
    Test updating user password by Admin and logging in with the new password.
    """
    login_admin = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    admin_token = login_admin.json()["access_token"]
    
    # Get juansup ID from repository directly
    with get_db_conn() as conn:
        user = UserRepository.get_by_username(conn, "juansup")
        user_id = user["id"]
        
    # Change password
    response = client.put(
        f"/api/users/{user_id}/password",
        json={"password": "newsuperpassword456"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    
    # Attempt login with old password -> should fail
    response_old = client.post(
        "/api/auth/login",
        data={"username": "juansup", "password": "superpassword123"}
    )
    assert response_old.status_code == 401
    
    # Attempt login with new password -> should succeed
    response_new = client.post(
        "/api/auth/login",
        data={"username": "juansup", "password": "newsuperpassword456"}
    )
    assert response_new.status_code == 200
    assert "access_token" in response_new.json()

def test_user_deactivation():
    """
    Test user deactivation: deactivating a user, preventing login, and preventing self-deactivation.
    """
    login_admin = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    admin_token = login_admin.json()["access_token"]
    
    with get_db_conn() as conn:
        # Get admin user ID
        admin_db = UserRepository.get_by_username(conn, "admin")
        admin_id = admin_db["id"]
        
        # Get juansup ID
        user_db = UserRepository.get_by_username(conn, "juansup")
        user_id = user_db["id"]
        
    # 1. Prevent admin from deactivating themselves
    response_self = client.put(
        f"/api/users/{admin_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response_self.status_code == 400
    assert response_self.json()["error"]["code"] == "SELF_DEACTIVATION_FORBIDDEN"
    
    # 2. Deactivate supervisor user juansup
    response_deact = client.put(
        f"/api/users/{user_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response_deact.status_code == 200
    
    # 3. Verify deactivated user login is blocked
    response_login = client.post(
        "/api/auth/login",
        data={"username": "juansup", "password": "newsuperpassword456"}
    )
    assert response_login.status_code == 401
    assert response_login.json()["error"]["code"] == "USER_INACTIVE"
