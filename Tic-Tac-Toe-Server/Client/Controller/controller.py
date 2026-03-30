from Client.View.view import View
from Client.View.login_window import LoginWindow
from Client.View.upload_pfp_window import UploadPFPWindow
import tkinter as tk

class Controller:
    def __init__(self, model, queue):
        self.model = model
        self.queue = queue

        self.root = tk.Tk()
        self.root.withdraw()

        self.login_window = LoginWindow(self, self.root)
        self.upload_pfp_window = UploadPFPWindow(self, self.root)
        self.view = View(self, self.root)
        self.my_id = None
        self.is_game_started = False

        self.flag = False


    def poll_queue(self) -> None:
        while not self.queue.empty():
            packet = self.queue.get()
            print(f"CONTROLLER: Received decrypted packet: {packet}")
            p_type = packet.get("type")
            p_data = packet.get("data")

            if p_type == "init":
                self.my_id = p_data["your_id"]
                self.view.update_player_name(f"Player {self.my_id}")
                self.view.status_label.config(text=f"CONNECTED AS PLAYER {self.my_id}")

            elif p_type == "game_ready":
                self.is_game_started = True
                if self.my_id == 1:
                    self.view.unlock_board("YOUR TURN")
                else:
                    self.view.lock_board("WAITING FOR PLAYER 1...")

            elif p_type == "update":
                field = p_data["field"]
                next_turn = p_data["next_turn"]
                winner = p_data["winner"]

                self.view.update_board(field)

                if winner:
                    self.view.show_winner(winner)
                    self.is_game_started = False
                elif next_turn == self.my_id:
                    self.view.unlock_board("YOUR TURN")
                else:
                    self.view.lock_board("OPPONENT'S TURN")

            elif p_type == "avatar":
                path = p_data.get("path")
                if path:
                    self.view.update_avatar(path)

            elif p_type == "error":
                print(f"Server Error: {packet.get('message')}")

        self.root.after(100, self.poll_queue)


    def send_move(self, row: int, col: int) -> None:
        # Sends move coordinates to the game server
        if self.is_game_started:
            self.model.send_move(row, col)
            self.view.lock_board("SENDING MOVE...")


    def verification(self, username: str, password: str, action: str) -> None:
        print("Verification method called in Controller")
        def cb(result):
            print("Checking verification in callback")
            self.check_verification(result, action)

        self.model.verification(username, password, action, callback=cb)


    def check_verification(self, result: bool, action: str) -> None:
        if result and action == "signup":
            self.login_window.show_connection("Welcome!")
            self.login_window.root.destroy()
            self.upload_pfp_window.start()
            return

        elif result and action == "login":
            self.login_window.show_connection("Welcome back!")
            self.login_window.root.destroy()
            self.view.start()
            self.model.send_ready(need_avatar=True)
            self.poll_queue()
            return

        elif not result:
            self.login_window.show_verif_status("Wrong username or password. Use signup if you dont have an account.")

        self.view.root.after(200, self.check_verification)


    def avatar_selected(self, image_path: str | None) -> None:

        if image_path:
            print("Avatar selected method called in Controller: " + image_path)
            self.model.send_avatar(image_path)

        self.view.start()

        if image_path:
            self.view.update_avatar(image_path)

        self.model.send_ready(need_avatar=False)
        self.poll_queue()


    def is_connected(self) -> None:
        if self.model.is_connected():
            self.login_window.show_connection("connected to server")
            self.login_window.enable_button()
            return
        elif not self.flag:
            self.flag = True
            self.login_window.disable_button()
            self.login_window.show_connection("not connected")

        self.view.root.after(1000, self.is_connected)


    def start(self):
        self.model.start()
        self.login_window.start()
        self.is_connected()
        self.root.mainloop()


    def stop(self):
        self.model.stop()
        self.root.destroy()