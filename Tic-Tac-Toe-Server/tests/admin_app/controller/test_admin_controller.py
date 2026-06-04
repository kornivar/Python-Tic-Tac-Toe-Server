import pytest
import tkinter as tk
from unittest.mock import MagicMock, patch, call
from queue import Queue
from AdminApp.Controller.controller import Controller


@pytest.fixture
def mock_mvc_dependencies():
    with patch('AdminApp.Controller.controller.tk.Tk') as mock_tk, \
            patch('AdminApp.Controller.controller.LoginWindow') as mock_login, \
            patch('AdminApp.Controller.controller.DetailsWindow') as mock_details, \
            patch('AdminApp.Controller.controller.BlacklistWindow') as mock_blacklist, \
            patch('AdminApp.Controller.controller.View') as mock_view:
        mock_root = MagicMock()
        mock_tk.return_value = mock_root

        model = MagicMock()
        queue = MagicMock(spec=Queue)

        yield model, queue, mock_root, mock_login, mock_details, mock_blacklist, mock_view


@pytest.fixture
def controller_instance(mock_mvc_dependencies):
    model, queue, _, _, _, _, _ = mock_mvc_dependencies
    return Controller(model, queue)



class TestControllerInitialization:
    def test_init_sets_default_states(self, controller_instance, mock_mvc_dependencies):
        model, queue, mock_root, mock_login, mock_details, mock_blacklist, mock_view = mock_mvc_dependencies

        assert controller_instance.model == model
        assert controller_instance.queue == queue
        assert controller_instance.root == mock_root

        mock_root.protocol.assert_called_once_with("WM_DELETE_WINDOW", controller_instance.on_closing)
        mock_root.withdraw.assert_called_once()

        mock_login.assert_called_once_with(controller_instance, mock_root)
        mock_details.assert_called_once_with(controller_instance, mock_root)
        mock_blacklist.assert_called_once_with(controller_instance, mock_root)
        mock_view.assert_called_once_with(controller_instance, mock_root)

        assert controller_instance.flag is False
        assert controller_instance.is_authenticated is False
        assert controller_instance.current_sessions == {}
        assert controller_instance.banned_users == []
        assert controller_instance.search_query == ""
        assert controller_instance.search_category == "Session ID"



class TestControllerQueuePolling:
    def test_poll_queue_empty(self, controller_instance):
        controller_instance.queue.empty.return_value = True
        controller_instance.poll_queue()
        controller_instance.root.after.assert_called_once_with(100, controller_instance.poll_queue)

    def test_poll_queue_process_update_packet_windows_visible(self, controller_instance):
        packet = {
            "type": "update",
            "data": {
                "sessions": {"1": {"user": "player1"}},
                "banned_users": ["banned_user_1"]
            }
        }

        controller_instance.queue.empty.side_effect = [False, True]
        controller_instance.queue.get.return_value = packet

        controller_instance.view.root.winfo_exists.return_value = True
        controller_instance.view.root.winfo_viewable.return_value = True

        controller_instance.blacklist_window.root.winfo_exists.return_value = True
        controller_instance.blacklist_window.root.winfo_viewable.return_value = True

        controller_instance.details_window.root.winfo_exists.return_value = True
        controller_instance.details_window.root.winfo_viewable.return_value = True
        controller_instance.details_window.session_id = 1

        controller_instance.poll_queue()

        assert controller_instance.current_sessions == {"1": {"user": "player1"}}
        assert controller_instance.banned_users == ["banned_user_1"]

        controller_instance.view.update_sessions.assert_called_once_with({"1": {"user": "player1"}})
        controller_instance.blacklist_window.update_list.assert_called_once_with(["banned_user_1"])
        controller_instance.details_window.update_info.assert_called_once_with({"user": "player1"})

    def test_poll_queue_process_update_packet_session_not_found_hides_details(self, controller_instance):
        packet = {
            "type": "update",
            "data": {"sessions": {}, "banned_users": []}
        }
        controller_instance.queue.empty.side_effect = [False, True]
        controller_instance.queue.get.return_value = packet

        controller_instance.view.root.winfo_exists.return_value = False
        controller_instance.blacklist_window.root.winfo_exists.return_value = False

        controller_instance.details_window.root.winfo_exists.return_value = True
        controller_instance.details_window.root.winfo_viewable.return_value = True
        controller_instance.details_window.session_id = 999

        controller_instance.poll_queue()

        controller_instance.details_window.hide_window.assert_called_once()

    def test_poll_queue_process_error_packet(self, controller_instance):
        packet = {"type": "error", "message": "Database disconnected"}
        controller_instance.queue.empty.side_effect = [False, True]
        controller_instance.queue.get.return_value = packet

        with patch('builtins.print') as mock_print:
            controller_instance.poll_queue()
            mock_print.assert_any_call("Server Error: Database disconnected")