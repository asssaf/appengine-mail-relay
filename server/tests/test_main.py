import json
import time
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

def test_health_success(client, mock_services, setup_env):
    # Mock monitoring results
    mock_series = mock_services.get_successful_sends.return_value
    mock_series.points[0].value.int64_value = 10

    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {}
    mock_services.get_successful_sends.assert_called_once()

def test_health_admin_notification(client, mock_services, setup_env):
    # Mock monitoring results with a trigger value
    mock_series = mock_services.get_successful_sends.return_value
    mock_series.points[0].value.int64_value = 60

    mock_services.get_application_id.return_value = "test-project"

    response = client.get('/health')
    assert response.status_code == 200
    mock_services.send_admin_email.assert_called_once_with(
        sender='noreply@test-project.appspotmail.com',
        subject="appengine-mail-relay admin notification",
        body="Messages sent at 60"
    )

def test_key_generation(client):
    response = client.get('/key')
    assert response.status_code == 200
    data = response.json
    assert "private_key" in data
    assert "public_key" in data

def test_notification_success(client, mock_services, monkeypatch):
    # Generate a real key pair for signing
    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key
    public_key_hex = verify_key.encode(encoder=HexEncoder).decode('ascii')

    monkeypatch.setenv('PUBLIC_KEY', public_key_hex)
    monkeypatch.setenv('SEND_TO', 'test@example.com')
    mock_services.get_application_id.return_value = "test-project"
    mock_services.get_successful_sends.return_value = None

    payload = {
        "body": "Hello World",
        "timestamp": int(time.time())
    }
    message = json.dumps(payload, separators=(',', ':')).encode('ascii')
    signed_message = signing_key.sign(message, encoder=HexEncoder)

    response = client.post('/notification', json={
        "signature": signed_message.decode('ascii')
    })

    assert response.status_code == 200
    mock_services.send_email.assert_called_once_with(
        sender='noreply@test-project.appspotmail.com',
        recipient='test@example.com',
        body="Hello World"
    )

def test_notification_invalid_signature(client, setup_env):
    response = client.post('/notification', json={
        "signature": "a" * 128 # Invalid signature
    })
    assert response.status_code == 401

def test_notification_expired_timestamp(client, mock_services, monkeypatch):
    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key
    public_key_hex = verify_key.encode(encoder=HexEncoder).decode('ascii')

    monkeypatch.setenv('PUBLIC_KEY', public_key_hex)

    payload = {
        "body": "Hello World",
        "timestamp": int(time.time()) - 300 # 5 minutes ago
    }
    message = json.dumps(payload, separators=(',', ':')).encode('ascii')
    signed_message = signing_key.sign(message, encoder=HexEncoder)

    response = client.post('/notification', json={
        "signature": signed_message.decode('ascii')
    })

    assert response.status_code == 400

def test_notification_missing_signature(client, setup_env):
    response = client.post('/notification', json={})
    assert response.status_code == 401
