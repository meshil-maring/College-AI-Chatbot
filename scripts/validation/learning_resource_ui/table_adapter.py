"""Small PostgREST-shaped transport for real repositories in the owned database."""

import json
import re
from types import SimpleNamespace

from academic_workspace.runtime import execute

READABLE = {'conversations', 'messages', 'knowledge_chunks', 'document_processing_runs',
            'document_versions', 'documents', 'knowledge_sources', 'chat_turns'}
WRITABLE = {'conversations', 'messages'}


def identifier(value):
    if not re.fullmatch(r'[a-z_]+', value):
        raise ValueError('Expected a known SQL identifier')
    return value


class Table:
    def __init__(self, adapter, name, literal):
        if name not in READABLE:
            raise ValueError('Unsupported repository table')
        self.adapter, self.name, self.literal = adapter, name, literal
        self.columns, self.filters, self.suffix = '*', [], ''
        self.action, self.payload, self.single = 'select', None, False

    def select(self, columns):
        self.columns = ', '.join(identifier(column.strip()) for column in columns.split(','))
        return self

    def eq(self, column, value):
        self.filters.append(f'{identifier(column)} = {self.literal(value)}')
        return self

    def in_(self, column, values):
        self.filters.append(f'{identifier(column)} IN ({", ".join(self.literal(value) for value in values)})')
        return self

    def order(self, column, desc=False):
        self.suffix += f' ORDER BY {identifier(column)} ' + ('DESC' if desc else 'ASC')
        return self

    def limit(self, count):
        self.suffix += f' LIMIT {int(count)}'
        return self

    def maybe_single(self):
        self.single = True
        return self

    def insert(self, payload):
        self.action, self.payload = 'insert', payload
        return self

    def update(self, payload):
        self.action, self.payload = 'update', payload
        return self

    def execute(self):
        where = ' WHERE ' + ' AND '.join(self.filters) if self.filters else ''
        if self.action == 'select':
            query = f'SELECT {self.columns} FROM public.{self.name}{where}{self.suffix}'
        else:
            if self.name not in WRITABLE:
                raise ValueError('Only owned conversation/message persistence is supported')
            columns = [identifier(column) for column in self.payload]
            values = [self.literal(value) for value in self.payload.values()]
            if self.action == 'insert':
                query = f'INSERT INTO public.{self.name} ({", ".join(columns)}) VALUES ({", ".join(values)}) RETURNING *'
            else:
                assignments = ', '.join(f'{column} = {value}' for column, value in zip(columns, values))
                query = f'UPDATE public.{self.name} SET {assignments}{where} RETURNING *'
        prefix = "SET request.jwt.claim.role = 'service_role'; SET ROLE service_role;"
        if self.action == 'select':
            sql = f"SELECT COALESCE(jsonb_agg(to_jsonb(row)), '[]') FROM ({query}) row;"
        else:
            sql = f"WITH rows AS ({query}) SELECT COALESCE(jsonb_agg(to_jsonb(row)), '[]') FROM rows row;"
        rows = json.loads(execute(self.adapter.container, prefix + sql))
        return SimpleNamespace(data=(rows[0] if rows else None) if self.single else rows)
