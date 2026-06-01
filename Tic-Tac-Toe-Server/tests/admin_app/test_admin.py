import pytest
import json
from unittest.mock import MagicMock, patch, mock_open
from AdminApp.admin import load_config, main


class TestAdminConfig:
    @patch("builtins.open", new_callable=mock_open, read_data='{"IP": "127.0.0.1", "PORT": 5000, "KEY": "test_key"}')
    @patch("json.load")
    def test_load_config_success(self, mock_json_load, mock_file):
        expected_config = {"IP": "127.0.0.1", "PORT": 5000, "KEY": "test_key"}
        mock_json_load.return_value = expected_config

        result = load_config("config.json")

        mock_file.assert_called_once_with("config.json", "r")
        mock_json_load.assert_called_once()
        assert result == expected_config

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_load_config_file_not_found(self, mock_file):
        with pytest.raises(FileNotFoundError):
            load_config("missing.json")


class TestAdminExecutionFlow:
    @patch("AdminApp.admin.Controller")
    @patch("AdminApp.admin.Model")
    @patch("AdminApp.admin.Fernet")
    @patch("AdminApp.admin.load_config")
    @patch("queue.Queue")
    def test_main_execution_initialization(
            self, mock_queue_cls, mock_load_config, mock_fernet_cls, mock_model_cls, mock_controller_cls
    ):
        mock_config = {
            "IP": "192.168.1.1",
            "PORT": 9999,
            "KEY": "Z29vZF9jcnlwdG9fYTJjX2tleV9leGFtcGxlXzMyYnl0ZXM="
        }
        mock_load_config.return_value = mock_config

        mock_queue_instance = MagicMock()
        mock_queue_cls.return_value = mock_queue_instance

        mock_cipher_instance = MagicMock()
        mock_fernet_cls.return_value = mock_cipher_instance

        mock_model_instance = MagicMock()
        mock_model_cls.return_value = mock_model_instance

        mock_controller_instance = MagicMock()
        mock_controller_cls.return_value = mock_controller_instance

        main()

        mock_load_config.assert_called_with("config.json")
        mock_fernet_cls.assert_called_once_with(mock_config["KEY"].encode('utf-8'))

        mock_model_cls.assert_called_once_with(
            mock_config["IP"],
            mock_config["PORT"],
            mock_queue_instance,
            mock_cipher_instance
        )
        mock_controller_cls.assert_called_once_with(mock_model_instance, mock_queue_instance)

        mock_controller_instance.start.assert_called_once()