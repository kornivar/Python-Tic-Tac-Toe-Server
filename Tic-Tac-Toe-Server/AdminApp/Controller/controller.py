from AdminApp.View.view import View
from AdminApp.View.login_window import LoginWindow
import tkinter as tk
import os

class Controller:
    def __init__(self, model, queue):
        self.model = model
        self.queue = queue

        self.root = tk.Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.withdraw()

        self.login_window = LoginWindow(self, self.root)

        self.view = View(self, self.root)

        self.flag = False


    def poll_queue(self) -> None:
        while not self.queue.empty():
            packet = self.queue.get()

            print(f"CONTROLLER: Received decrypted packet: {packet}")

            p_type = packet.get("type")
            p_data = packet.get("data")

            if p_type == "init":
                pass
                # sessions = p_data
                # if sessions is not None:
                #     self.view.update_sessions(sessions)

            elif p_type == "update":
                sessions = p_data
                if sessions is not None:
                    self.view.update_sessions(sessions)

            elif p_type == "error":
                print(f"Server Error: {packet.get('message')}")

        self.root.after(100, self.poll_queue)


    def verification(self, username: str, password: str, action: str) -> None:
        print("Verification method called in Controller")
        def cb(result):
            print("Checking verification in callback")
            self.check_verification(result, action)

        self.model.verification(username, password, action, callback=cb)


    def check_verification(self, result: bool, action: str) -> None:
        if result and action == "login":
            self.login_window.show_connection("Welcome!")
            self.login_window.root.destroy()
            self.view.start()
            self.model.send_ready()
            self.poll_queue()
            return

        elif not result:
            self.login_window.show_verif_status("Wrong username or password.")

        self.view.root.after(200, self.check_verification)


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


    def pause_session(self, session_id: int) -> None:
        self.model.pause_session(session_id)


    def resume_session(self, session_id: int) -> None:
        self.model.resume_session(session_id)


    def start(self):
        self.model.start()
        self.login_window.start()
        self.is_connected()
        self.root.mainloop()


    def on_closing(self):
        print("Closing admin...")

        self.model.stop()

        try:
            self.model.socket.close()
        except:
            pass

        self.root.destroy()

        os._exit(0)