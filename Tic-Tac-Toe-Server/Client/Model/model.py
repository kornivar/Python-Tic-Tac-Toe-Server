import socket
import threading
import time
import json
import os
import base64
from cryptography.fernet import Fernet

class Model:
    def __init__(self, ip, port, queue, cipher):
        self.ip = ip
        self.port = port
        self.queue = queue
        self.cipher  = cipher

        self.my_id = None
        self.running = False
        self.username = None
        self.connected = False

        self._callback = None

        self.client = None
        self.receive_thread = None
        self.connect_thread = None


    def receive(self) -> None:
        buffer = b""

        while self.running:
            try:
                data = self.client.recv(1024)
                if not data:
                    break

                buffer += data

                while b"\n" in buffer:
                    message, buffer = buffer.split(b"\n", 1)

                    print(f"CLIENT: Received encrypted message: {message}")

                    decrypted = self.cipher.decrypt(message)
                    decoded = decrypted.decode("utf-8")

                    packet = json.loads(decoded)

                    p_type = packet.get("type")
                    p_data = packet.get("data")

                    if p_type == "init":
                        self.my_id = p_data["your_id"]
                        self.queue.put({"type": "init", "data": p_data})

                    elif p_type == "identify_request":

                        print("server requested identification")

                        self.identify()

                    elif p_type == "update":
                        self.queue.put({"type": "update", "data": p_data})

                    elif p_type == "game_ready":
                        self.queue.put({"type": "game_ready", "data": p_data})

                    elif p_type == "avatar":
                        self.set_avatar(p_data)

                    elif p_type == "game_error":
                        self.queue.put({"type": "game_error", "data": p_data})

                    elif p_type == "error":
                        self.queue.put({"type": "error", "data": p_data})

                    elif p_type == "response":
                        if hasattr(self, "_callback") and self._callback:
                            self._callback(p_data)

            except Exception as e:
                print(f"Receive error: {e}")
                break

        self.running = False
        self.client.close()


    def send_move(self, row: int, col: int) -> None:
        if not self.running:
            return

        move_payload = {
            "row": row,
            "col": col
        }

        packet = self.to_packet(move_payload, "move")
        packet_bytes = packet.encode('utf-8')
        encrypted_packet = self.cipher.encrypt(packet_bytes)
        self.client.sendall(encrypted_packet + b"\n")


    def send_avatar(self, file_path: str) -> None:
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

        packet_bytes = json.dumps(packet).encode('utf-8')
        encrypted_packet = self.cipher.encrypt(packet_bytes)

        self.client.sendall(encrypted_packet + b"\n")

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                self.client.sendall(chunk)


    def send_ready(self, need_avatar=False) -> None:
        if not self.running:
            return

        packet = {
            "type": "ready",
            "data": {
                "need_avatar": need_avatar
            }
        }

        packet_bytes = json.dumps(packet).encode('utf-8')
        encrypted_packet = self.cipher.encrypt(packet_bytes)

        self.client.sendall(encrypted_packet + b"\n")


    @staticmethod
    def to_packet(data, d_type="move") -> str | None:
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
        elif d_type == "identify":
            packet = {
                "type": "identify",
                "data": data
            }
            return json.dumps(packet)

        return None


    def verification(self, username: str, password: str, action: str, callback=None) -> None:
        if self.client:
            self._callback = callback
            self.username = username
            if action == "login":
                data = {
                    "username": username,
                    "password": password,
                }
                packet = self.to_packet(data, "login")
                packet_bytes = packet.encode('utf-8')
                encrypted_packet = self.cipher.encrypt(packet_bytes)
                self.client.sendall(encrypted_packet + b"\n")

            elif action == "signup":
                data = {
                    "username": username,
                    "password": password,
                }
                packet = self.to_packet(data, "signup")
                packet_bytes = packet.encode('utf-8')
                encrypted_packet = self.cipher.encrypt(packet_bytes)
                self.client.sendall(encrypted_packet + b"\n")


    def set_avatar(self, data: dict) -> None:
        if not self.running:
            return

        if data.get("exists"):
            avatar_bytes = base64.b64decode(data["content"])
            filename = data.get("filename", "avatar.png")

            cache_dir = "ClientCache"
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


    def identify(self) -> None:
        data = "user"
        packet = self.to_packet(data, "identify")
        packet_bytes = packet.encode('utf-8')
        encrypted_packet = self.cipher.encrypt(packet_bytes)
        self.client.sendall(encrypted_packet + b"\n")


    def is_connected(self):
        return self.connected


    def connect(self) -> None:
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
            print("Client stopped")
        except:
            pass