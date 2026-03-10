import socket
import threading
import time
import queue
import json

class Model:
    def __init__(self, ip, port, queue):
        self.ip = ip
        self.port = port
        self.queue = queue

        self.verified = False
        self.running = False

        self.client = None
        self.receive_thread = None
        self.connect_thread = None


    def receive(self):
        buffer = ""

        while self.running:
            try:
                data = self.client.recv(1024)

                if not data:
                    break

                buffer += data.decode()

                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)

                    packet = json.loads(message)

                    p_type = packet["type"]
                    p_data = packet["data"]

                    if p_type == "message":
                        if p_data == "stop":
                            self.running = False
                        else:
                            self.queue.put(p_data)

                    elif p_type == "response":
                        self.verified = p_data

            except Exception as e:
                print("Receive error:", e)
                break

        self.running = False
        self.client.close()


    def send(self, message):
        if not self.running:
            return

        packet = self.to_packet(message)

        if packet:
            self.client.sendall((packet + "\n").encode())

        if message == "stop":
            self.running = False


    @staticmethod
    def to_packet(data, d_type ="message"):
        if  d_type == "login":
            packet = {
                "type": "login",
                "data": data
            }
            return json.dumps(packet)
        elif d_type == "signup":
            packet = {
                "type": "signup",
                "data": data
            }
            return json.dumps(packet)
        elif  d_type == "message":
            packet = {
                "type": "message",
                "data": data
            }
            return json.dumps(packet)

        return None


    def verification(self, username, password, action):
        if self.client:
            if action == "login":
                data = {
                    "username": username,
                    "password": password,
                }
                packet = self.to_packet(data, "login")
                self.client.sendall((packet + '\n').encode())

            elif action == "signup":
                data = {
                    "username": username,
                    "password": password,
                }
                packet = self.to_packet(data, "signup")
                self.client.sendall((packet + '\n').encode())

    def is_connected(self):
        if not self.connect_thread.is_alive():
            return True
        else:
            return False


    def connect(self):
        while True:
            try:
                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client.connect((self.ip, self.port))
                break
            except (ConnectionRefusedError, socket.timeout, OSError):
                if self.client:
                    self.client.close()
                time.sleep(1)

        self.receive_thread = threading.Thread(
            target=self.receive,
            daemon=False
        )
        self.receive_thread.start()


    def start(self):
        self.running = True

        self.connect_thread = threading.Thread(
            target=self.connect,
            daemon=False
        )
        self.connect_thread.start()


    def stop(self):
        self.running = False

        try:
            self.client.close()
        except:
            pass

        if self.receive_thread:
            self.receive_thread.join()

        print(f"Client stopped")
