"""Colocated PostgREST and RPC doubles for student metadata tests."""

from unittest.mock import MagicMock


def _norm(value):
    if isinstance(value, bool):
        return str(value)
    return None if value is None else str(value)


def _or_matches(row, expression):
    """Evaluate the single PostgREST ``or_`` expression this phase builds."""
    for clause in expression.split(","):
        clause = clause.strip()
        if clause.endswith(".is.null"):
            column = clause[: -len(".is.null")]
            if row.get(column) is None:
                return True
        elif ".gte." in clause:
            column, _, threshold = clause.partition(".gte.")
            value = row.get(column)
            if value is not None and str(value) >= threshold:
                return True
        else:  # pragma: no cover - defensive: unknown clause does not filter
            return True
    return False


class _FakeQueryBuilder:
    """Minimal PostgREST query builder that really filters/orders/limits rows.

    Recording every operation lets the tests assert the exact server-side
    filters (tenant scoping, publication filter, expiry filter) instead of
    trusting the projection alone.
    """

    def __init__(self, table_name, rows, calls):
        self._table = table_name
        self._rows = list(rows)
        self._calls = calls
        self._orders: list[tuple[str, bool]] = []
        self._limit: int | None = None

    def select(self, columns):
        self._calls.append((self._table, "select", columns))
        return self

    def eq(self, column, value):
        self._calls.append((self._table, "eq", column, value))
        self._rows = [r for r in self._rows if _norm(r.get(column)) == _norm(value)]
        return self

    def neq(self, column, value):
        self._calls.append((self._table, "neq", column, value))
        self._rows = [r for r in self._rows if _norm(r.get(column)) != _norm(value)]
        return self

    def or_(self, expression):
        self._calls.append((self._table, "or_", expression))
        self._rows = [r for r in self._rows if _or_matches(r, expression)]
        return self

    def order(self, column, desc=False):
        self._calls.append((self._table, "order", column, desc))
        self._orders.append((column, desc))
        return self

    def limit(self, count):
        self._calls.append((self._table, "limit", count))
        self._limit = count
        return self

    def execute(self):
        self._calls.append((self._table, "execute"))
        rows = list(self._rows)
        # PostgREST treats the FIRST `order` as the primary sort key, so the
        # orders are applied from least to most significant (Python's sort is
        # stable, which preserves the higher-precedence keys).
        for column, desc in reversed(self._orders):
            rows.sort(
                key=lambda r, c=column: (_norm(r.get(c)) is None, _norm(r.get(c))),
                reverse=desc,
            )
        if self._limit is not None:
            rows = rows[: self._limit]
        return MagicMock(data=rows)


class _FakeClient:
    """Fake Supabase client holding one row set per table name."""

    def __init__(self, tables=None):
        self.tables = tables or {}
        self.calls: list[tuple] = []

    def table(self, name):
        return _FakeQueryBuilder(name, self.tables.get(name, []), self.calls)

    def rpc(self, name, parameters):
        # The database integration suite tests role policy. This double supplies
        # the requested published fixture page and records trusted actor/scope.
        assert name == 'read_knowledge_resources'
        assert parameters['actor']
        self.calls.append(('rpc', name, parameters))
        query = self.table('knowledge_sources').eq('institution_id', parameters['tenant'])
        query = query.eq('lifecycle_status', 'published')
        for source_type in parameters['excluded_types']:
            query = query.neq('source_type', source_type)
        rows = query.order('created_at', desc=True).limit(parameters['page_limit']).execute().data
        return MagicMock(execute=MagicMock(return_value=MagicMock(data={'items': rows})))

    def operations(self, table, operation):
        return [c for c in self.calls if c[0] == table and c[1] == operation]
