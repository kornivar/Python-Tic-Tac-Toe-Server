class ClientData:
    def __init__(self, conn, addr, id, is_win):
        self._conn = conn
        self._addr = addr
        self._id = id
        self.is_win = is_win
        self.is_authenticated = False
        self.is_ready = False
        self.username = None

    @property
    def conn(self):
        return self._conn

    @property
    def addr(self):
        return self._addr

    @property
    def id(self):
        return self._id