import os
import pytest

# Set TESTING environment variable before importing the app
os.environ['TESTING'] = 'true'

import server.main as main_module
from server.main import app as flask_app

@pytest.fixture(autouse=True)
def reset_verify_key_cache():
    main_module._verify_key_cache = None
    yield
    main_module._verify_key_cache = None

@pytest.fixture
def app():
    flask_app.config.update({
        "TESTING": True,
    })
    yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def mock_services(mocker):
    return mocker.patch('server.main.services', autospec=True)

@pytest.fixture
def setup_env(monkeypatch):
    monkeypatch.setenv('PUBLIC_KEY', '0000000000000000000000000000000000000000000000000000000000000000')
    monkeypatch.setenv('SEND_TO', 'test@example.com')
    monkeypatch.setenv('GOOGLE_CLOUD_PROJECT', 'test-project')
