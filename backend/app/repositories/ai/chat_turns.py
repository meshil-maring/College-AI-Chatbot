"""Durable chat-turn RPC transport; identity is supplied by the server."""


def call(client, operation, **parameters):
    return client.rpc(operation, parameters).execute().data
