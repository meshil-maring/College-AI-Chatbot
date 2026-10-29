"""Real workflow RPCs over the owned container; fictional storage/embeddings only."""

import json
import re
from types import SimpleNamespace

from academic_workspace.runtime import execute

OPERATIONS = {
    "read_knowledge_resources", "read_knowledge_revisions", "save_knowledge_draft",
    "register_knowledge_upload", "retry_knowledge_index", "decide_knowledge_revision",
    "read_resource_chat_context", "search_audience_knowledge_chunks",
    "snapshot_knowledge_policy", "check_knowledge_policy",
    "claim_chat_turn", "read_chat_turn", "complete_chat_turn", "fail_chat_turn",
    "read_conversation_citations",
}


def literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, (dict, list)):
        return literal(json.dumps(value)) + "::jsonb"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


class RpcFailure(Exception):
    def __init__(self, failure):
        match = re.search(r"ERROR:\s+([A-Z0-9]{5}):", str(failure))
        self.code = match.group(1) if match else "UNKNOWN"
        super().__init__("Disposable PostgreSQL rejected the operation: " + self.code)


class DatabaseAdapter:
    def __init__(self, container):
        self.container = container
        self.objects = {}

    def table(self, name):
        from table_adapter import Table
        return Table(self, name, literal)

    def rpc(self, operation, parameters):
        if operation not in OPERATIONS or any(
            not re.fullmatch(r"[a-z_]+", name) for name in parameters
        ):
            raise ValueError("Only the resource workflow RPCs are supported")

        def perform():
            arguments = []
            for name, value in parameters.items():
                if name == 'query_embedding':
                    encoded = literal(json.dumps(value)) + '::extensions.vector'
                elif name in {'chunks', 'selected_messages'}:
                    encoded = 'ARRAY[' + ','.join(literal(item) for item in value) + ']::uuid[]'
                else:
                    encoded = literal(value)
                arguments.append(f'{name} => {encoded}')
            arguments = ', '.join(arguments)
            query = f'SELECT to_jsonb(public.{operation}({arguments}));'
            if operation == 'search_audience_knowledge_chunks':
                query = f"SELECT COALESCE(jsonb_agg(to_jsonb(row)), '[]') FROM public.{operation}({arguments}) row;"
            try:
                output = execute(self.container, f"""
                    SET request.jwt.claim.role = 'service_role';
                    SET ROLE service_role;
                    {query}
                """)
            except RuntimeError as failure:
                print(f"Disposable RPC {operation} rejected: {failure}", flush=True)
                raise RpcFailure(failure) from failure
            return SimpleNamespace(data=json.loads(output))

        return SimpleNamespace(execute=perform)

    def upload(self, client, bucket, key, data, mime):
        self.objects[(bucket, key)] = data

    def delete(self, client, bucket, key):
        self.objects.pop((bucket, key), None)

    def process(self, run_id):
        """Use real manifest/index guards; replace only the external provider work."""
        location = json.loads(execute(self.container, f"""
            SELECT jsonb_build_array(v.storage_bucket, v.storage_object_key)
            FROM public.document_processing_runs r
            JOIN public.document_versions v USING (document_version_id)
            WHERE r.processing_run_id = {literal(run_id)}::uuid;
        """))
        content = self.objects[tuple(location)].decode("utf-8")
        vector = "[1," + "0," * 1534 + "0]"
        execute(self.container, f"""
            BEGIN;
            SET LOCAL request.jwt.claim.role = 'service_role';
            SET LOCAL ROLE service_role;
            UPDATE public.document_processing_runs
                SET status = 'ready', embedding_status = 'embedded', completed_at = now()
                WHERE processing_run_id = {literal(run_id)}::uuid;
            WITH chunk AS (
                INSERT INTO public.knowledge_chunks(processing_run_id, chunk_sequence, content_text)
                VALUES ({literal(run_id)}::uuid, 1, {literal(content)}) RETURNING chunk_id
            )
            INSERT INTO public.chunk_embeddings(chunk_id, model_name, embedding_dimensions, embedding)
                SELECT chunk_id, 'fixture-only', 1536, {literal(vector)}::extensions.vector FROM chunk;
            COMMIT;
        """)
        return {"status": "ready"}
