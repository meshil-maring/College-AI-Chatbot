from .support import (
    INST_A1,
    JR_A,
    MR_A,
    ORG_A,
    STUDENT_ID_A1,
    SimpleNamespace,
    uuid4,
)


class _Table:
    """Chainable query builder answering reads/writes from ``state``."""

    def __init__(self, state: dict, name: str):
        self._state = state
        self._name = name
        self._filters: list[tuple] = []
        self._single = False
        self._payload = None
        self._mode = None
        self._in_filter = None

    def select(self, *a, **k):
        self._state.setdefault("accesses", [])
        if self._name not in self._state["accesses"]:
            self._state["accesses"].append(self._name)
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def ilike(self, column, value):
        self._filters.append((column, value, "ilike"))
        return self

    def in_(self, column, values):
        self._in_filter = (column, [str(v) for v in values])
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def maybe_single(self):
        self._single = True
        return self

    def insert(self, payload):
        self._mode = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._mode = "update"
        self._payload = payload
        return self

    def upsert(self, payload, on_conflict=None):
        self._mode = "upsert"
        self._payload = payload
        return self

    def delete(self):
        self._mode = "delete"
        return self

    def _rows(self):
        rows = self._state.get(self._name, [])
        if isinstance(rows, dict):
            rows = list(rows.values())

        def match(row):
            for f in self._filters:
                if len(f) == 3:
                    col, value, _ = f
                    if str(row.get(col, "")).lower() != str(value).lower():
                        return False
                else:
                    col, value = f
                    if str(row.get(col, "")) != str(value):
                        return False
            if self._in_filter:
                col, values = self._in_filter
                if str(row.get(col, "")) not in values:
                    return False
            return True

        return [row for row in rows if match(row)]

    def execute(self):
        if self._mode == "delete":
            doomed = self._rows()
            table = self._state.get(self._name, [])
            if isinstance(table, list):
                self._state[self._name] = [r for r in table if r not in doomed]
            return SimpleNamespace(data=[])
        if self._mode in ("insert", "upsert"):
            row = dict(self._payload)
            if self._mode == "upsert":
                existing = self._rows()
                if existing:
                    existing[0].update(row)
                    return SimpleNamespace(data=[existing[0]])
            defaults = {
                "students": ("student_id", STUDENT_ID_A1),
                "institution_membership_requests": ("request_id", MR_A),
                "institutions": ("institution_id", INST_A1),
                "organizations": ("organization_id", ORG_A),
                "institution_join_requests": ("join_request_id", JR_A),
            }
            if self._name in defaults:
                key, value = defaults[self._name]
                row.setdefault(key, value)
            table = self._state.setdefault(self._name, [])
            if isinstance(table, dict):
                table.setdefault(str(row.get("user_id", uuid4())), row)
            else:
                table.append(row)
            return SimpleNamespace(data=[row])
        if self._mode == "update":
            updated = self._rows()
            for row in updated:
                row.update(self._payload)
                if self._name == "institutions":
                    # Emulate trg_phase613_institutions_status.
                    row["is_active"] = row.get("status") == "active"
            return SimpleNamespace(data=updated)
        rows = self._rows()
        if self._single:
            return SimpleNamespace(data=rows[0] if rows else None)
        return SimpleNamespace(data=rows)


class _FakeClient:
    """Permissive fake Supabase client for the whole request pipeline."""

    def __init__(self, tables=None):
        self.state: dict = {"accesses": []}
        if tables:
            self.state.update(tables)

    def table(self, name):
        return _Table(self.state, name)
