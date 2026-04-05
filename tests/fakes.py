class FakeCursor:
    def __init__(
        self,
        *,
        fetchone_results=None,
        fetchall_results=None,
        rowcount=1,
        lastrowid=1,
        raise_on_execute=None,
    ):
        self._fetchone_results = list(fetchone_results or [])
        self._fetchall_results = list(fetchall_results or [])
        self.rowcount = rowcount
        self.lastrowid = lastrowid
        self.raise_on_execute = raise_on_execute
        self.executed = []
        self.closed = False

    def execute(self, query, params=None):
        self.executed.append((query, params))
        if self.raise_on_execute:
            raise self.raise_on_execute

    def fetchone(self):
        if self._fetchone_results:
            return self._fetchone_results.pop(0)
        return None

    def fetchall(self):
        if self._fetchall_results:
            return self._fetchall_results.pop(0)
        return []

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self, dictionary=False):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True
