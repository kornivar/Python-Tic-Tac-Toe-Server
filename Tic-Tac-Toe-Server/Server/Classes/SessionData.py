import json
class SessionData:
    def __init__(self, session_id):
        self._session_id = session_id
        self.players = {}  # {player_id: ClientData}
        self.playing_field = [[0, 0, 0] for _ in range(3)]
        self.current_turn = 1
        self.is_active = True
        self.ready_players = set()

    def check_winner(self):
        field = self.playing_field
        # Rows and columns
        for i in range(3):
            if field[i][0] == field[i][1] == field[i][2] != 0:
                return field[i][0]
            if field[0][i] == field[1][i] == field[2][i] != 0:
                return field[0][i]
        # Diagonals
        if field[0][0] == field[1][1] == field[2][2] != 0:
            return field[0][0]
        if field[0][2] == field[1][1] == field[2][0] != 0:
            return field[0][2]
        # Draw
        if not any(0 in row for row in field):
            return "draw"
        return None

    def broadcast(self, encrypted_packet):
        for p_id in self.players:
            try:
                self.players[p_id].conn.sendall(encrypted_packet + b"\n")
            except:
                pass

    @property
    def session_id(self):
        return self._session_id
