import pytest
import socket
import threading
import json
import base64
from unittest.mock import MagicMock, patch, mock_open, call
from queue import Queue
from cryptography.fernet import Fernet
from Client.Model.model import Model


@pytest.fixture
def mock_dependencies():
    ip = "127.0.0.1"
    port = 9090
    queue = MagicMock(spec=Queue)
    cipher = MagicMock(spec=Fernet)
    return ip, port, queue, cipher

@pytest.fixture
def model_instance(mock_dependencies):
    ip, port, queue, cipher = mock_dependencies
    return Model(ip, port, queue, cipher)



class TestClientModelInitialization:
    def test_initial_state(self, model_instance, mock_dependencies):
        ip, port, queue, cipher = mock_dependencies
        assert model_instance.ip == ip
        assert model_instance.port == port
        assert model_instance.queue == queue
        assert model_instance.cipher == cipher
        assert model_instance.my_id is None
        assert model_instance.running is False
        assert model_instance.username is None
        assert model_instance.connected is False
        assert model_instance._callback is None
        assert model_instance.client is None



class TestClientModelStaticMethods:
    @pytest.mark.parametrize("d_type, data, expected_type", [
        ("move", {"row": 1, "col": 2}, "move"),
        ("login", {"user": "player"}, "login"),
        ("signup", {"user": "new_player"}, "signup"),
        ("identify", "user", "identify")
    ])
    def test_to_packet_valid_types(self, d_type, data, expected_type):
        result = Model.to_packet(data, d_type)
        parsed = json.loads(result)
        assert parsed["type"] == expected_type
        assert parsed["data"] == data

    def test_to_packet_invalid_type(self):
        assert Model.to_packet({"data": 1}, "unknown_type") is None



class TestClientModelNetworkCommands:
    def test_send_move_when_running(self, model_instance):
        model_instance.running = True
        model_instance.client = MagicMock()
        model_instance.cipher.encrypt.return_value = b"encrypted_move"

        model_instance.send_move(1, 2)

        model_instance.cipher.encrypt.assert_called_once()
        model_instance.client.sendall.assert_called_once_with(b"encrypted_move\n")

    def test_send_move_when_not_running(self, model_instance):
        model_instance.running = False
        model_instance.client = MagicMock()

        model_instance.send_move(1, 2)
        model_instance.client.sendall.assert_not_called()

    @pytest.mark.parametrize("action, expected_type", [
        ("login", "login"),
        ("signup", "signup")
    ])
    def test_verification_actions(self, model_instance, action, expected_type):
        model_instance.client = MagicMock()
        model_instance.cipher.encrypt.return_value = b"encrypted_auth"
        callback = MagicMock()

        model_instance.verification("player1", "pass123", action, callback)

        assert model_instance._callback == callback
        assert model_instance.username == "player1"
        model_instance.client.sendall.assert_called_once_with(b"encrypted_auth\n")

    def test_send_ready(self, model_instance):
        model_instance.running = True
        model_instance.client = MagicMock()
        model_instance.cipher.encrypt.return_value = b"encrypted_ready"

        model_instance.send_ready(need_avatar=True)

        model_instance.client.sendall.assert_called_once_with(b"encrypted_ready\n")

    def test_identify(self, model_instance):
        model_instance.client = MagicMock()
        model_instance.cipher.encrypt.return_value = b"encrypted_identify"

        model_instance.identify()

        model_instance.client.sendall.assert_called_once_with(b"encrypted_identify\n")