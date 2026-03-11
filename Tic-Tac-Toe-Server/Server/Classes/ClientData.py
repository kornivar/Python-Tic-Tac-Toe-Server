class ClientData:
    def __init__(self, conn, addr, id, is_win):
        self._conn = conn
        self._addr = addr
        self._id = id
        self._is_win = is_win

    @property
    def conn(self):
        return self._conn

    @property
    def addr(self):
        return self._addr

    @property
    def id(self):
        return self._id

    @property
    def is_win(self):
        return self._is_win