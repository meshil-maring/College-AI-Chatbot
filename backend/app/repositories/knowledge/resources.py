"""Knowledge workflow RPC transport; callers provide server-resolved identity."""


def call(client, operation: str, **parameters):
    return client.rpc(operation, parameters).execute().data


def search_chunks(client, embedding, *, actor, tenant, top_k, model_name, **filters):
    return call(
        client, 'search_audience_knowledge_chunks', actor=str(actor),
        query_embedding=list(embedding), match_count=top_k,
        filter_institution_id=str(tenant), filter_model_name=model_name,
        **{f'filter_{key}': str(value) if value is not None else None for key, value in filters.items()},
    ) or []
