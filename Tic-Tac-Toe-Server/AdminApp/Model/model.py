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

                    print(f"ADMIN: Received encrypted message: {message}")

                    decrypted = self.cipher.decrypt(message)
                    decoded = decrypted.decode("utf-8")

                    packet = json.loads(decoded)

                    p_type = packet.get("type")
                    p_data = packet.get("data")

                    if p_type == "identify_request":

                        print("server requested identification")

                        self.identify()

                    elif p_type == "update":
                        self.queue.put({"type": "update", "data": p_data})

                    elif p_type == "error":
                        self.queue.put({"type": "error", "message": packet.get("message")})

                    elif p_type == "response":
                        if hasattr(self, "_callback") and self._callback:
                            self._callback(p_data)

            except Exception as e:
                print(f"Receive error: {e}")
                break

        self.running = False
        self.client.close()


    @staticmethod
    def to_packet(data, d_type="login") -> str | None:

        if  d_type == "login":
            packet = {
                "type": "login",
                "data": data
            }
            return json.dumps(packet)
        elif d_type == "identify":
            packet = {
                "type": "identify",
                "data": data
            }
            return json.dumps(packet)
        elif d_type == "admin_command":
            packet = {
                "type": "admin_command",
                "data": data
            }
            return json.dumps(packet)

        return None


    def verification(self, username: str, password: str, action: str, callback=None) -> None:
        if self.running:
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
        return


    def identify(self) -> None:
        if self.running:
            data = "admin"
            packet = self.to_packet(data, "identify")
            packet_bytes = packet.encode('utf-8')
            encrypted_packet = self.cipher.encrypt(packet_bytes)
            self.client.sendall(encrypted_packet + b"\n")
        return


    def pause_session(self, session_id: int) -> None:
        if self.running:
            data = {
                "type": "session",
                "session_id": session_id,
                "state": "pause"
            }
            packet = self.to_packet(data, "admin_command")
            packet_bytes = packet.encode('utf-8')
            encrypted_packet = self.cipher.encrypt(packet_bytes)
            self.client.sendall(encrypted_packet + b"\n")


    def resume_session(self, session_id: int) -> None:
        if self.running:
            data = {
                "type": "session",
                "session_id": session_id,
                "state": "resume"
            }
            packet = self.to_packet(data, "admin_command")
            packet_bytes = packet.encode('utf-8')
            encrypted_packet = self.cipher.encrypt(packet_bytes)
            self.client.sendall(encrypted_packet + b"\n")


    def is_connected(self):
        return self.connected


    def send_ready(self) -> None:
        if not self.running:
            return

        packet = {
            "type": "ready",
            "data": {}
        }

        packet_bytes = json.dumps(packet).encode('utf-8')
        encrypted_packet = self.cipher.encrypt(packet_bytes)

        self.client.sendall(encrypted_packet + b"\n")


    def send_ban_unban_command(self, session_id: int | None, user_id: int | None, username: str, action: str) -> None:
        data = {
            "type": "user",
            "session_id": session_id,
            "user_id": user_id,
            "username": username,
            "action": action
        }

        packet = self.to_packet(data, "admin_command")
        packet_bytes = packet.encode('utf-8')
        encrypted_packet = self.cipher.encrypt(packet_bytes)
        self.client.sendall(encrypted_packet + b"\n")


    def connect(self) -> None:
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
            print("Client stopped")
            self.client.close()
        except:
            pass