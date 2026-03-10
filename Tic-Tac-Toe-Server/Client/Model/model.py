import socket
import threading
import time
import json


class Model:
    def __init__(self, ip, port, queue):
        self.ip = ip
        self.port = port
        self.queue = queue

        self.my_id = None
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

                    p_type = packet.get("type")
                    p_data = packet.get("data")

                    if p_type == "init":
                        # Server sends initial ID and board
                        self.my_id = p_data["your_id"]
                        self.queue.put({"type": "init", "data": p_data})

                    elif p_type == "update":
                        # Server sends board update, next turn, and winner status
                        self.queue.put({"type": "update", "data": p_data})

                    elif p_type == "game_ready":
                        self.queue.put({"type": "game_ready", "data": p_data})

                    elif p_type == "error":
                        # Server reports invalid move
                        self.queue.put({"type": "error", "message": packet.get("message")})

            except Exception as e:
                print(f"Receive error: {e}")
                break

        self.running = False
        try:
            self.client.close()
        except:
            pass


    def send_move(self, row, col):
        # Send a move coordinates to the server
        if not self.running:
            return

        move_payload = {
            "row": row,
            "col": col
        }

        packet = self.to_packet(move_payload, "move")
        self.client.sendall((packet + "\n").encode())


    @staticmethod
    def to_packet(data, d_type="move"):
        # Wrap data into a standardized JSON packet string
        packet = {
            "type": d_type,
            "data": data
        }
        return json.dumps(packet)


    def is_connected(self):
        # Check if the connection thread has finished
        if self.connect_thread and not self.connect_thread.is_alive():
            return True
        return False


    def connect(self):
        # Attempt to establish connection
        while self.running:
            try:
                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client.connect((self.ip, self.port))
                print(f"Connected to {self.ip}:{self.port}")
                break
            except (ConnectionRefusedError, socket.timeout, OSError):
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