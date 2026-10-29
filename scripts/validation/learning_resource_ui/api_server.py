"""Loopback-only bridge to the actual FastAPI resource routes and real SQL."""

from contextlib import contextmanager, ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from academic_workspace.runtime import execute
from database_adapter import literal
from app.api.knowledge import resources, resource_uploads
from app.core.application import validation_error_handler, unhandled_error_handler
from app.core.errors import AppError, app_error_handler
from app.services.knowledge.resources import operations, uploads


def identities(container):
    records = {}
    for role in ("admin", "faculty", "staff"):
        key = "tenant_actor" if role == "admin" else "wf_" + role
        record = json.loads(execute(container, f"""
            SELECT jsonb_build_object(
                'authenticated', true, 'user_id', u.id, 'auth_user_id', u.auth_user_id,
                'email', u.email, 'role', {literal(role)},
                'institution_id', knowledge_fixture.id('tenant'), 'institution_code', 'TENANT-KNOWLEDGE-TEST',
                'effective_permissions', (
                    SELECT jsonb_agg(p.code) FROM public.permissions p
                    JOIN public.role_permissions rp ON rp.permission_id = p.permission_id
                    JOIN public.roles r ON r.id = rp.role_id
                    WHERE r.name = {literal(role)} AND p.is_active AND r.is_active
                )) FROM public.users u WHERE u.id = knowledge_fixture.id({literal(key)});
        """))
        records[role] = record
    return records


@contextmanager
def serve(adapter):
    records = identities(adapter.container)
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
    app.include_router(resource_uploads.router, prefix="/api/v1")
    app.include_router(resources.router, prefix="/api/v1")

    def current_user(request: Request):
        role = request.headers.get("authorization", "").removeprefix("Bearer fixture-")
        if role not in records:
            raise AppError("Fictional test identity required", 401, "UNAUTHORIZED")
        return {**records[role], "roles": [role], "permissions_resolved": True,
                "authorization_context": SimpleNamespace(role=role)}

    for dependency in (resources._READ, resources._WRITE, resource_uploads._WRITE):
        app.dependency_overrides[dependency] = current_user

    @app.get("/api/v1/auth/me")
    def me(request: Request):
        user = current_user(request)
        return records[user["role"]]

    with ExitStack() as stack:
        from chat_adapter import connect
        connect(app, stack, adapter, current_user)
        stack.enter_context(patch.object(operations, "get_admin_client", return_value=adapter))
        stack.enter_context(patch.object(uploads, "get_r2_client", return_value=adapter))
        stack.enter_context(patch.object(uploads, "upload_file", side_effect=adapter.upload))
        stack.enter_context(patch.object(uploads, "delete_file", side_effect=adapter.delete))
        stack.enter_context(patch.object(uploads, "process_run_to_retrieval", side_effect=adapter.process))
        client = stack.enter_context(TestClient(app, raise_server_exceptions=False))

        class Handler(BaseHTTPRequestHandler):
            def forward(self):
                if not self.path.startswith(("/api/v1/knowledge/", "/api/v1/conversations", "/api/v1/generation/turns/")) and self.path not in {
                    "/api/v1/auth/me", "/api/v1/generation/chat",
                }:
                    self.send_error(404)
                    return
                size = int(self.headers.get("content-length", "0"))
                if size > 100000:
                    self.send_error(413)
                    return
                response = client.request(
                    self.command, self.path, content=self.rfile.read(size),
                    headers={key: value for key, value in self.headers.items()
                             if key.lower() not in {"host", "content-length", "connection"}},
                )
                self.send_response(response.status_code)
                self.send_header("content-type", response.headers.get("content-type", "application/json"))
                self.send_header("content-length", str(len(response.content)))
                self.end_headers()
                try:
                    self.wfile.write(response.content)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass  # Browser navigation may cancel an otherwise completed read.

            do_GET = do_POST = do_PATCH = forward

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield client, f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)
