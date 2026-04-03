import json

from pip._internal.network import session


class SessionData:
    def __init__(self, session_id):
        self._session_id = session_id
        self.players = {}  # {player_id: ClientData}
        self.playing_field = [[0, 0, 0] for _ in range(3)]
        self.current_turn = 1
        self.state = "inactive"
        self.ready_players = set()

    def to_dict(self):
        return {
            "session_id": self._session_id,
            "state": self.state,
            "players": {p_id: p_obj.to_dict() for p_id, p_obj in self.players.items()}
        }

    def check_winner(self):
        field = self.playing_field
        # Rows and columns
        for i in range(3):
            if field[i][0] == field[i][1] == field[i][2] != 0:
                self.state = "finished"
                return field[i][0]
            if field[0][i] == field[1][i] == field[2][i] != 0:
                self.state = "finished"
                return field[0][i]
        # Diagonals
        if field[0][0] == field[1][1] == field[2][2] != 0:
            self.state = "finished"
            return field[0][0]
        if field[0][2] == field[1][1] == field[2][0] != 0:
            self.state = "finished"
            return field[0][2]
        # Draw
        if not any(0 in row for row in field):
            self.state = "finished"
            return "draw"

        return None


    def broadcast(self, encrypted_packet):
        for p_id in self.players:
            try:
                self.players[p_id].conn.sendall(encrypted_packet + b"\n")
            except Exception as e:
                print(f"Error in Session {self._session_id} broadcast function: {e}")


    def send_error(self, encrypted_packet, target_id: int):
        if target_id:
                try:
                    self.players[target_id].conn.sendall(encrypted_packet + b"\n")
                except Exception as e:
                    print(f"Error in Session {self._session_id} send_error function: {e}")
        else:
            return


    def reset_session(self):
        self.state = "inactive"
        self.ready_players.clear()
        self.playing_field = [[0, 0, 0] for _ in range(3)]
        self.current_turn = 1


    def pause_session(self, cipher):
        self.state = "paused"
        packet = {
            "type": "admin_command",
            "data": {"command": "pause"}
        }
        packet_bytes = json.dumps(packet).encode('utf-8')
        encrypted_packet = cipher.encrypt(packet_bytes)
        self.broadcast(encrypted_packet)


    def resume_session(self, cipher):
        self.state = "active"
        packet = {
            "type": "admin_command",
            "data": {
                "command": "resume",
                "next_turn": self.current_turn,
                "field": self.playing_field
                }
        }
        packet_bytes = json.dumps(packet).encode('utf-8')
        encrypted_packet = cipher.encrypt(packet_bytes)
        self.broadcast(encrypted_packet)

    def remove_player_from_session(self, user_id: int, sessions_dict: dict, cipher):
        if user_id in self.players:
            conn_to_close = self.players[user_id].conn
            del self.players[user_id]

            try:
                conn_to_close.close()
            except:
                pass

        if len(self.players) == 0:
            if self._session_id in sessions_dict:
                del sessions_dict[self._session_id]
                print(f"Session {self._session_id} deleted (no players left).")
        else:
            self.reset_session()
            disconnect_msg = {
                "type": "game_error",
                "data": {"message": "Your opponent was banned and kicked."}
            }
            packet_bytes = json.dumps(disconnect_msg).encode('utf-8')
            try:
                self.broadcast(cipher.encrypt(packet_bytes))
            except:
                pass


    @property
    def session_id(self):
        return self._session_id
