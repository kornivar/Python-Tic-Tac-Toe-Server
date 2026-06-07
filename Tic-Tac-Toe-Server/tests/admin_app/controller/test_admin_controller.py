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



class TestControllerVerification:
    def test_verification_calls_model_with_callback(self, controller_instance):
        controller_instance.verification("admin", "secret", "login")

        controller_instance.model.verification.assert_called_once()
        args, kwargs = controller_instance.model.verification.call_args
        assert args[0] == "admin"
        assert args[1] == "secret"
        assert args[2] == "login"
        assert callable(kwargs["callback"])

    def test_check_verification_success(self, controller_instance):
        controller_instance.is_authenticated = False

        controller_instance.check_verification(True, "login")

        assert controller_instance.is_authenticated is True
        controller_instance.login_window.show_connection.assert_called_once_with("Welcome!")
        controller_instance.login_window.root.destroy.assert_called_once()
        controller_instance.view.start.assert_called_once()
        controller_instance.model.send_ready.assert_called_once()

    def test_check_verification_failure(self, controller_instance):
        controller_instance.is_authenticated = False

        controller_instance.check_verification(False, "login")

        assert controller_instance.is_authenticated is False
        controller_instance.login_window.show_verif_status.assert_called_once_with("Wrong username or password.")

    def test_check_verification_already_authenticated(self, controller_instance):
        controller_instance.is_authenticated = True

        controller_instance.check_verification(True, "login")

        controller_instance.login_window.show_connection.assert_not_called()



class TestControllerConnectionHandling:
    def test_is_connected_true(self, controller_instance):
        controller_instance.model.is_connected.return_value = True

        controller_instance.is_connected()

        controller_instance.login_window.show_connection.assert_called_once_with("connected to server")
        controller_instance.login_window.enable_button.assert_called_once()

    def test_is_connected_false_first_trigger(self, controller_instance):
        controller_instance.model.is_connected.return_value = False
        controller_instance.flag = False

        controller_instance.is_connected()

        assert controller_instance.flag is True
        controller_instance.login_window.disable_button.assert_called_once()
        controller_instance.login_window.show_connection.assert_called_once_with("not connected")
        controller_instance.view.root.after.assert_called_once_with(1000, controller_instance.is_connected)



class TestControllerSessionManagement:
    def test_pause_session(self, controller_instance):
        controller_instance.pause_session(15)
        controller_instance.model.pause_session.assert_called_once_with(15)

    def test_resume_session(self, controller_instance):
        controller_instance.resume_session(15)
        controller_instance.model.resume_session.assert_called_once_with(15)

    def test_show_blacklist(self, controller_instance):
        controller_instance.banned_users = ["user1", "user2"]
        controller_instance.show_blacklist()

        controller_instance.blacklist_window.update_list.assert_called_once_with(["user1", "user2"])
        controller_instance.blacklist_window.show.assert_called_once()

    @pytest.mark.parametrize("session_id, user_id, username, should_ban, expected_action", [
        (10, 5, "cheater", True, "ban"),
        (None, None, "toxic_user", False, "unban")
    ])
    def test_toggle_ban(self, controller_instance, session_id, user_id, username, should_ban, expected_action):
        controller_instance.toggle_ban(session_id, user_id, username, should_ban)

        controller_instance.model.send_ban_unban_command.assert_called_once_with(
            session_id=session_id,
            user_id=user_id,
            username=username,
            action=expected_action
        )

    def test_show_details_when_session_exists(self, controller_instance):
        session_data = {"user": "target"}
        controller_instance.current_sessions = {"101": session_data}

        controller_instance.show_details(101)

        controller_instance.details_window.start.assert_called_once_with(session_data)

    def test_show_details_when_session_missing(self, controller_instance):
        controller_instance.current_sessions = {}
        controller_instance.show_details(404)
        controller_instance.details_window.start.assert_not_called()