"""Two independent service transactions cannot claim the same turn twice."""

from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier
from uuid import uuid4

from academic_workspace.runtime import execute


def verify_turn_race(container):
    identities = json.loads(execute(container, """
        SELECT jsonb_build_object('actor', knowledge_fixture.id('wf_staff'), 'tenant', knowledge_fixture.id('tenant'));
    """))
    actor, tenant = identities['actor'], identities['tenant']
    turn_id, conversation = str(uuid4()), str(uuid4())
    barrier = Barrier(2)
    statement = f"""
        SET request.jwt.claim.role = 'service_role';
        SET ROLE service_role;
        SELECT public.claim_chat_turn('{actor}', '{tenant}', '{turn_id}', '{conversation}', '{conversation}', 'Concurrent question');
    """

    def claim():
        barrier.wait(timeout=10)
        return json.loads(execute(container, statement))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(claim) for _ in range(2)]
        results = [future.result(timeout=30) for future in futures]
    assert sorted(result['state'] for result in results) == ['claimed', 'processing']
    assert execute(container, f"SELECT count(*) FROM public.messages WHERE conversation_id = '{conversation}'") == '1'
    print('PASS: simultaneous service transactions claim one worker and save one question', flush=True)
