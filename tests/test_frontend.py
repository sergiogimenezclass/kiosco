import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add project root directory to path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
settings.DB_PATH = "test_kiosco.db"

from app.main import app

client = TestClient(app)

def test_frontend_root_redirection():
    """
    Test that GET / redirects to /static/index.html.
    """
    response = client.get("/", follow_redirects=False)
    assert response.status_code in [302, 307]
    assert response.headers["location"] == "/static/index.html"

def test_frontend_index_html():
    """
    Test that GET /static/index.html is served successfully
    and includes links to styles.css and app.js.
    """
    response = client.get("/static/index.html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    html_content = response.text
    # Verificar que el HTML referencia los estáticos correctos
    assert "css/styles.css" in html_content
    assert "js/app.js" in html_content
    assert "Kiosco" in html_content or "kiosco" in html_content or "POS" in html_content

def test_frontend_js_and_css_assets():
    """
    Test that core frontend assets (JS and CSS) are served correctly.
    """
    # Test CSS
    response_css = client.get("/static/css/styles.css")
    assert response_css.status_code == 200
    assert "text/css" in response_css.headers["content-type"]
    assert len(response_css.content) > 0

    # Test JS
    response_js = client.get("/static/js/app.js")
    assert response_js.status_code == 200
    assert any(mime in response_js.headers["content-type"] for mime in ["application/javascript", "text/javascript", "application/x-javascript"])
    assert len(response_js.content) > 0
