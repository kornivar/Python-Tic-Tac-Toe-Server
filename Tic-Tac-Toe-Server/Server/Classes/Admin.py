import hashlib
import json
from cryptography.fernet import Fernet

class Admin:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.is_authenticated = False
        self.role = None
        self.last_sessions_hash = None


    def update_sessions(self, sessions, banned_users, cipher, stop_event):
        while not stop_event.is_set():
            try:
                serializable_sessions = {
                    s_id: s_obj.to_dict() for s_id, s_obj in sessions.items()
                }

                full_data = {
                    "sessions": serializable_sessions,
                    "banned_users": list(banned_users)
                }

                current_data_str = json.dumps(full_data, sort_keys=True)
                current_hash = hashlib.md5(current_data_str.encode()).hexdigest()

                if current_hash == self.last_sessions_hash:
                    continue

                print(f"Sending update to admin at {self.addr}")
                self.last_sessions_hash = current_hash

                packet = {
                    "type": "update",
                    "data": full_data
                }

                packet_bytes = json.dumps(packet).encode('utf-8')
                encrypted_packet = cipher.encrypt(packet_bytes)
                self.conn.sendall(encrypted_packet + b"\n")

            except Exception as e:
                print(f"Failed to send update to admin: {e}")

            stopped = stop_event.wait(timeout=2)
            if stopped:
                break