import socket
import threading
import time
import json
import os
import base64

class Model:
    def __init__(self, ip, port, queue):
        self.ip = ip
        self.port = port
        self.queue = queue

        self.my_id = None
        self.running = False
        self.verified = False
        self.username = None
        self.connected = False

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

                    p_type = packet.get("type")
                    p_data = packet.get("data")

                    if p_type == "init":
                        self.my_id = p_data["your_id"]
                        self.queue.put({"type": "init", "data": p_data})

                    elif p_type == "update":
                        self.queue.put({"type": "update", "data": p_data})

                    elif p_type == "game_ready":
                        self.queue.put({"type": "game_ready", "data": p_data})

                    elif p_type == "avatar":
                        if p_data.get("exists"):
                            avatar_bytes = base64.b64decode(p_data["content"])
                            filename = p_data.get("filename", "avatar.png")

                            cache_dir = "client_cache"
                            os.makedirs(cache_dir, exist_ok=True)
                            local_path = os.path.join(cache_dir, filename)

                            with open(local_path, "wb") as f:
                                f.write(avatar_bytes)

                            self.queue.put({
                                "type": "avatar",
                                "data": {"path": local_path}
                            })
                        else:
                            self.queue.put({
                                "type": "avatar",
                                "data": {"path": None}
                            })

                    elif p_type == "error":
                        self.queue.put({"type": "error", "message": packet.get("message")})

                    elif p_type == "response":
                        self.verified = p_data

            except Exception as e:
                print(f"Receive error: {e}")
                break

        self.running = False
        self.client.close()

    def send_move(self, row, col):
        if not self.running:
            return

        move_payload = {
            "row": row,
            "col": col
        }

        packet = self.to_packet(move_payload, "move")
        self.client.sendall((packet + "\n").encode())

    def send_avatar(self, file_path):
        if not self.running:
            return

        size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)

        packet = {
            "type": "avatar",
            "data": {
                "username": self.username,
                "filename": filename,
                "size": size
            }
        }

        self.client.sendall((json.dumps(packet) + "\n").encode())

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                self.client.sendall(chunk)

    def send_ready(self, need_avatar=False):
        if not self.running:
            return

        packet = {
            "type": "ready",
            "data": {
                "need_avatar": need_avatar
            }
        }

        self.client.sendall((json.dumps(packet) + "\n").encode())


    @staticmethod
    def to_packet(data, d_type="move"):
        if d_type == "move":
            # Wrap data into a standardized JSON packet string
            packet = {
                "type": d_type,
                "data": data
            }
            return json.dumps(packet)
        elif  d_type == "login":
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

        return None


    def verification(self, username, password, action):
        if self.client:
            if action == "login":
                self.username = username
                data = {
                    "username": username,
                    "password": password,
                }
                packet = self.to_packet(data, "login")
                self.client.sendall((packet + '\n').encode())

            elif action == "signup":
                self.username = username
                data = {
                    "username": username,
                    "password": password,
                }
                packet = self.to_packet(data, "signup")
                self.client.sendall((packet + '\n').encode())


    def is_connected(self):
        return self.connected


    def connect(self):
        # Attempt to establish connection
        while self.running:
            try:
                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client.connect((self.ip, self.port))
                self.connected = True
                print(f"Connected to {self.ip}:{self.port}")
                break
            except (ConnectionRefusedError, socket.timeout, OSError):
                self.connected = False
                if self.client:
                    self.client.close()
                time.sleep(1)

        if self.running:
            self.receive_thread = threading.Thread(
                target=self.receive,
                daemon=True
            )
            self.receive_thread.start()


    def start(self):
        self.running = True
        self.connect_thread = threading.Thread(
            target=self.connect,
            daemon=True
        )
        self.connect_thread.start()


    def stop(self):
        self.running = False
        try:
            self.client.close()
        except:
            pass
        print("Client stopped")