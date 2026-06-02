import pytest
import socket
import threading
import json
from unittest.mock import MagicMock, patch, call
from queue import Queue
from cryptography.fernet import Fernet
from AdminApp.Model.model import Model

@pytest.fixture
def mock_dependencies():
    ip = "127.0.0.1"
    port = 8080
    queue = MagicMock(spec=Queue)
    cipher = MagicMock(spec=Fernet)
    return ip, port, queue, cipher

@pytest.fixture
def model_instance(mock_dependencies):
    ip, port, queue, cipher = mock_dependencies
    return Model(ip, port, queue, cipher)


class TestModelInitialization:
    def test_init_state(self, model_instance, mock_dependencies):
        ip, port, queue, cipher = mock_dependencies
        assert model_instance.ip == ip
        assert model_instance.port == port
        assert model_instance.queue == queue
        assert model_instance.cipher == cipher
        assert model_instance.running is False
        assert model_instance.username is None
        assert model_instance.connected is False
        assert model_instance._callback is None
        assert model_instance.client is None


class TestModelStaticMethods:
    @pytest.mark.parametrize("d_type, data, expected_type", [
        ("login", {"user": "admin"}, "login"),
        ("identify", "admin", "identify"),
        ("admin_command", {"cmd": "clear"}, "admin_command")
    ])
    def test_to_packet_valid(self, d_type, data, expected_type):
        result = Model.to_packet(data, d_type)
        parsed = json.loads(result)
        assert parsed["type"] == expected_type
        assert parsed["data"] == data

    def test_to_packet_invalid_type(self):
        assert Model.to_packet("data", "invalid_type") is None


class TestModelNetworkCommands:
    def test_verification_when_running(self, model_instance):
        model_instance.running = True
        model_instance.client = MagicMock()
        model_instance.cipher.encrypt.return_value = b"encrypted_login"
        callback = MagicMock()

        model_instance.verification("admin_user", "password123", "login", callback)

        assert model_instance._callback == callback
        assert model_instance.username == "admin_user"
        model_instance.cipher.encrypt.assert_called_once()
        model_instance.client.sendall.assert_called_once_with(b"encrypted_login\n")

    def test_verification_when_not_running(self, model_instance):
        model_instance.running = False
        model_instance.client = MagicMock()

        model_instance.verification("admin_user", "password123", "login")
        model_instance.client.sendall.assert_not_called()

    def test_identify(self, model_instance):
        model_instance.running = True
        model_instance.client = MagicMock()
        model_instance.cipher.encrypt.return_value = b"encrypted_identify"

        model_instance.identify()

        model_instance.client.sendall.assert_called_once_with(b"encrypted_identify\n")

    def test_pause_session(self, model_instance):
        model_instance.running = True
        model_instance.client = MagicMock()
        model_instance.cipher.encrypt.return_value = b"encrypted_pause"

        model_instance.pause_session(42)

        model_instance.client.sendall.assert_called_once_with(b"encrypted_pause\n")

    def test_resume_session(self, model_instance):
        model_instance.running = True
        model_instance.client = MagicMock()
        model_instance.cipher.encrypt.return_value = b"encrypted_resume"

        model_instance.resume_session(42)

        model_instance.client.sendall.assert_called_once_with(b"encrypted_resume\n")

    def test_send_ready_when_running(self, model_instance):
        model_instance.running = True
        model_instance.client = MagicMock()
        model_instance.cipher.encrypt.return_value = b"encrypted_ready"

        model_instance.send_ready()

        model_instance.client.sendall.assert_called_once_with(b"encrypted_ready\n")

    def test_send_ready_when_not_running(self, model_instance):
        model_instance.running = False
        model_instance.client = MagicMock()

        model_instance.send_ready()

        model_instance.client.sendall.assert_not_called()

    def test_send_ban_unban_command(self, model_instance):
        model_instance.running = True
        model_instance.client = MagicMock()
        model_instance.cipher.encrypt.return_value = b"encrypted_ban"

        model_instance.send_ban_unban_command(1, 2, "target_user", "ban")

        model_instance.client.sendall.assert_called_once_with(b"encrypted_ban\n")


class TestModelStateAndLifecycle:
    def test_is_connected(self, model_instance):
        model_instance.connected = True
        assert model_instance.is_connected() is True
        model_instance.connected = False
        assert model_instance.is_connected() is False

    @patch('threading.Thread')
    def test_start(self, mock_thread, model_instance):
        model_instance.start()
        assert model_instance.running is True
        mock_thread.assert_called_once_with(target=model_instance.connect, daemon=True)

    def test_stop(self, model_instance):
        model_instance.client = MagicMock()
        model_instance.running = True

        model_instance.stop()

        assert model_instance.running is False
        model_instance.client.close.assert_called_once()

    def test_stop_with_exception_handling(self, model_instance):
        model_instance.client = MagicMock()
        model_instance.client.close.side_effect = Exception("Socket error")
        model_instance.running = True

        model_instance.stop()
        assert model_instance.running is False


class TestModelConnectMethod:
    @patch('socket.socket')
    @patch('time.sleep', return_value=None)
    @patch('threading.Thread')
    def test_connect_success_first_attempt(self, mock_thread, mock_sleep, mock_socket, model_instance):
        model_instance.running = True
        mock_sock_instance = MagicMock()
        mock_socket.return_value = mock_sock_instance

        model_instance.connect()

        assert model_instance.connected is True
        assert model_instance.client == mock_sock_instance
        mock_sock_instance.connect.assert_called_once_with((model_instance.ip, model_instance.port))
        mock_thread.assert_called_once_with(target=model_instance.receive, daemon=True)

    @patch('socket.socket')
    @patch('time.sleep', return_value=None)
    def test_connect_retry_on_exception(self, mock_sleep, mock_socket, model_instance):
        model_instance.running = True

        mock_sock_fail = MagicMock()
        mock_sock_fail.connect.side_effect = ConnectionRefusedError
        mock_sock_success = MagicMock()

        mock_socket.side_effect = [mock_sock_fail, mock_sock_success]

        def success_effect(address):
            model_instance.running = False
            return None

        mock_sock_success.connect.side_effect = success_effect

        model_instance.connect()

        assert mock_sock_fail.close.called
        mock_sleep.assert_called_once_with(1)