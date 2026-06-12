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