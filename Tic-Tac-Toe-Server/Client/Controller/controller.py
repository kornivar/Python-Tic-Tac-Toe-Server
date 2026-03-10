from Client.View.view import View
from Client.View.login_window import LoginWindow
import tkinter as tk

class Controller:
    def __init__(self, model, queue):
        self.model = model
        self.queue = queue

        self.root = tk.Tk()
        self.root.withdraw()

        self.login_window = LoginWindow(self, self.root)
        self.view = View(self, self.root)

        self.flag = False


    def poll_queue(self):
        while not self.queue.empty():
            message = self.queue.get()
            self.view.show_server_message(message)

        self.view.root.after(100, self.poll_queue)


    def to_stop_or_not_to_stop(self):
        if not self.model.running:
            self.view.show_info("stop used, disconnecting")
            self.model.stop()
            self.view.root.destroy()
            return

        self.view.root.after(1500, self.to_stop_or_not_to_stop)


    def send_message(self, message, selected = None):
        if selected is None or selected == "message":
            self.model.send(message)


    def show_message(self, message):
        self.view.show_server_message(message)


    def is_connected(self):
        if self.model.is_connected():
            self.login_window.show_connection("connected to server")
            self.login_window.enable_button()
            self.poll_queue()
            return
        elif not self.flag:
            self.flag = True
            self.login_window.disable_button()
            self.login_window.show_connection("not connected")

        self.view.root.after(1000, self.is_connected)


    def verification(self, username, password, action):
        print("Verification method called in Controller")
        self.model.verification(username, password, action)
        print("Checking verification in Controller")
        self.check_verification()


    def check_verification(self):
        if self.model.verified:
            self.login_window.show_connection("Welcome!")
            self.login_window.root.destroy()
            self.to_stop_or_not_to_stop()
            self.view.start()
            return

        self.view.root.after(200, self.check_verification)


    def show_info(self, message):
        self.view.show_info(message)


    def start(self):
        self.model.start()
        self.login_window.start()
        self.is_connected()
        self.root.mainloop()
