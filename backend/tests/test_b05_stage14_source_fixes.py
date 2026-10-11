"""Offline orchestration and source contracts; never PostgreSQL execution.

Atomicity below is simulated by an RPC fake. SQL engine rollback, trigger
execution, uniqueness and locking remain separate runtime validation items.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.main import app
from app.repositories import platform_admin_invitations as repo
from app.schemas.tenancy import ApprovalDecisionRequest
from app.services import platform_admin_invitations as institution
from app.services import super_admin_registration as platform
from app.services import tenancy
from app.services import student_registration as accounts

ROOT = Path(__file__).parents[2]
SQL = ROOT / 'supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql'
TOKEN = 'a' * 64
INV = '20000000-0000-0000-0000-000000000001'
USER = '30000000-0000-0000-0000-000000000001'
AUTH = '50000000-0000-0000-0000-000000000001'
INST = '40000000-0000-0000-0000-000000000001'
OP = '60000000-0000-0000-0000-000000000001'
ACTOR = {'user_id': USER, 'auth_user_id': AUTH}


@pytest.fixture
def recovery(monkeypatch):
    client = MagicMock()
    invitation = {'invitation_id':INV,'institution_id':INST,'role_name':'admin',
                  'email':'new@example.test','status':'accepted','acceptance_id':OP}
    operation = {'acceptance_id':OP,'stage':'accepted','user_id':USER,'auth_user_id':AUTH,'new_account':True}
    for service, resolver in ((institution,'_resolve_live_invitation'),(platform,'_resolve_live')):
        monkeypatch.setattr(service,'get_admin_client',lambda:client)
        monkeypatch.setattr(service,resolver,lambda *_:invitation.copy())
        monkeypatch.setattr(service.abuse,'enforce_accept_rate_limit',lambda *_:None)
        monkeypatch.setattr(service.abuse,'enforce_inspect_rate_limit',lambda *_:None)
    monkeypatch.setattr(institution,'_require_institution',lambda *_:{'name':'Example','code':'EX'})
    read = MagicMock(side_effect=lambda *a,**k:operation.copy())
    monkeypatch.setattr(repo,'recover_accepted_operation',read)
    def advance(*a,**k):
        if operation['stage'] != k['expected_stage']: return None
        operation['stage'] = k['stage']
        return operation.copy()
    monkeypatch.setattr(repo,'advance_operation',MagicMock(side_effect=advance))
    create = MagicMock()
    monkeypatch.setattr(accounts,'_create_auth_account',create)
    reserve, grant = MagicMock(), MagicMock()
    monkeypatch.setattr(repo,'reserve_invitation',reserve)
    monkeypatch.setattr(repo,'claim_invitation',grant)
    return client, invitation, operation, read, create, reserve, grant


@pytest.mark.parametrize('kind,path',[('institution','admin-invitations'),('platform','super-admin-invitations')])
def test_confirmation_failure_reload_and_retry_require_no_sign_in(recovery,kind,path):
    client, invitation, operation, read, create, reserve, grant = recovery
    http = TestClient(app)
    client.auth.admin.update_user_by_id.side_effect = [TimeoutError('lost confirmation'),None]
    endpoint = f'/api/v1/{path}/{TOKEN}'
    assert http.post(endpoint+'/recover').status_code == 502
    assert operation['stage'] == 'accepted' and invitation['status'] == 'accepted'
    assert http.get(endpoint).json()['account_recovery_available'] is True
    assert http.post(endpoint+'/recover').status_code == 200
    assert operation['stage'] == 'confirmed'
    # Lost final response/reload: another attempt returns without provider I/O.
    assert http.post(endpoint+'/recover',json={'auth_user_id':'forged','acceptance_id':'forged','password':'ignored'}).status_code == 200
    assert client.auth.admin.update_user_by_id.call_args_list == [
        call(AUTH,{'email_confirm':True}), call(AUTH,{'email_confirm':True}),
    ]
    read.assert_called_with(client,INV,repo.hash_invitation_token(TOKEN),kind=kind)
    create.assert_not_called(); reserve.assert_not_called(); grant.assert_not_called()


@pytest.mark.parametrize('result',[None,{'new_account':False,'stage':'accepted'},
                                  {'new_account':True,'stage':'provider_started'},
                                  {'new_account':True,'stage':'reserved'}])
def test_recovery_cannot_create_accounts_or_confirm_unvalidated_operations(recovery,result):
    client,_,_,read,create,reserve,grant = recovery
    read.side_effect = None; read.return_value = result
    response = TestClient(app).post(f'/api/v1/admin-invitations/{TOKEN}/recover')
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'INVITATION_RECONCILIATION_REQUIRED'
    client.auth.admin.update_user_by_id.assert_not_called()
    create.assert_not_called(); reserve.assert_not_called(); grant.assert_not_called()


def test_concurrent_confirmation_completion_repairs_a_lost_cas_response(recovery,monkeypatch):
    client,_,operation,_,create,_,grant = recovery
    def advance(*a,**k):
        operation['stage'] = 'confirmed'
        return None
    monkeypatch.setattr(repo,'advance_operation',advance)
    assert institution.recover_account(TOKEN).role == 'admin'
    client.auth.admin.update_user_by_id.assert_called_once_with(AUTH,{'email_confirm':True})
    create.assert_not_called(); grant.assert_not_called()


@pytest.mark.parametrize('path',['admin-invitations','super-admin-invitations'])
def test_lost_confirmation_record_response_returns_original_result_on_retry(recovery,monkeypatch,path):
    client,_,operation,_,create,reserve,grant = recovery
    def advance(*a,**k):
        operation['stage'] = 'confirmed'
        raise TimeoutError('state committed, response lost')
    monkeypatch.setattr(repo,'advance_operation',advance)
    http = TestClient(app,raise_server_exceptions=False)
    endpoint = f'/api/v1/{path}/{TOKEN}/recover'
    assert http.post(endpoint).status_code == 500
    assert http.post(endpoint).status_code == 200
    client.auth.admin.update_user_by_id.assert_called_once_with(AUTH,{'email_confirm':True})
    create.assert_not_called(); reserve.assert_not_called(); grant.assert_not_called()


@pytest.mark.parametrize('kind',['institution','platform'])
@pytest.mark.parametrize('status',['cancelled','expired'])
@pytest.mark.parametrize('failure',['before_audit','after_commit'])
def test_lifecycle_audit_failure_and_retry_use_one_durable_command(kind,status,failure):
    # This fake models the command's transaction boundary; it cannot prove SQL
    # rollback. It does exercise the real repository adapter and retry result.
    state = {'status':'invited','events':{},'decisions':0,'fault':failure}
    client = MagicMock()
    def rpc(name,params):
        assert name == 'b05_transition_invitation'
        assert params == {'p_kind':kind,'p_id':INV,'p_status':status,'p_actor':USER}
        def execute():
            candidate = deepcopy(state)
            repeated = candidate['status'] == status
            if not repeated:
                candidate['status'] = status; candidate['decisions'] += 1
            if state['fault'] == 'before_audit':
                state['fault'] = None
                raise RuntimeError('audit insertion failed')
            candidate['events'].setdefault((kind,INV,status),USER)
            candidate['fault'] = None
            state.update(candidate)
            if failure == 'after_commit' and not repeated:
                raise TimeoutError('response lost after commit')
            return SimpleNamespace(data={'closed':True,'audit_persisted':True,'already_applied':repeated})
        return SimpleNamespace(execute=execute)
    client.rpc.side_effect = rpc
    with pytest.raises((RuntimeError,TimeoutError)):
        repo.transition_invitation(client,INV,kind=kind,status=status,actor_user_id=USER)
    if failure == 'before_audit': assert state['status'] == 'invited' and not state['events']
    result = repo.transition_invitation(client,INV,kind=kind,status=status,actor_user_id=USER)
    assert result['audit_persisted'] is True
    assert state['status'] == status and state['decisions'] == 1 and len(state['events']) == 1
    # Repair a preexisting terminal state with missing audit, without deciding again.
    state['events'].clear()
    assert repo.transition_invitation(client,INV,kind=kind,status=status,actor_user_id=USER)['already_applied']
    assert state['decisions'] == 1 and len(state['events']) == 1
    client.table.assert_not_called()


@pytest.mark.parametrize('decision,status',[('approve','approved'),('reject','rejected')])
def test_legacy_decision_retry_routes_status_and_actor_to_atomic_rpc(monkeypatch,decision,status):
    client = MagicMock()
    monkeypatch.setattr(tenancy,'get_admin_client',lambda:client)
    monkeypatch.setattr(tenancy.tenancy_repo,'get_membership_request_by_id',lambda *_:{
        'request_id':INV,'institution_id':INST,'status':status})
    monkeypatch.setattr(tenancy,'assert_can_manage_institution',lambda *_:None)
    monkeypatch.setattr(tenancy,'assert_active_tenant_context',lambda *_:None)
    client.rpc.return_value.execute.return_value.data = {'decided':True,'audit_persisted':True,'already_applied':True}
    for _ in range(2):
        assert tenancy.decide_membership_request(ACTOR,{},INV,ApprovalDecisionRequest(decision=decision)).status == decision
    assert client.rpc.call_count == 2
    client.rpc.assert_called_with('b05_decide_legacy_membership',{
        'p_request_id':INV,'p_status':status,'p_actor_user_id':USER,'p_actor_auth_user_id':AUTH,'p_reason':None})
    client.table.assert_not_called()


def test_legacy_decision_missing_audit_never_reports_success(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(tenancy,'get_admin_client',lambda:client)
    monkeypatch.setattr(tenancy.tenancy_repo,'get_membership_request_by_id',lambda *_:{'request_id':INV,'institution_id':INST,'status':'pending'})
    monkeypatch.setattr(tenancy,'assert_can_manage_institution',lambda *_:None)
    monkeypatch.setattr(tenancy,'assert_active_tenant_context',lambda *_:None)
    client.rpc.return_value.execute.return_value.data = {'decided':True,'audit_persisted':False}
    with pytest.raises(AppError) as caught:
        tenancy.decide_membership_request(ACTOR,{},INV,ApprovalDecisionRequest(decision='approve'))
    assert caught.value.code == 'MEMBERSHIP_DECISION_CONFLICT'
    client.table.assert_not_called()


@pytest.mark.parametrize('fault',['grant','audit','lost_response'])
def test_legacy_decision_failure_and_retry_preserve_unrelated_grants(monkeypatch,fault):
    client = MagicMock()
    existing = {'user_id':USER,'scope_id':'other-institution','role':'faculty'}
    state = {'row':{'request_id':INV,'institution_id':INST,'status':'pending'},
             'grants':[existing.copy()],'audits':{},'decisions':0,'fault':fault}
    monkeypatch.setattr(tenancy,'get_admin_client',lambda:client)
    monkeypatch.setattr(tenancy.tenancy_repo,'get_membership_request_by_id',lambda *_:state['row'].copy())
    monkeypatch.setattr(tenancy,'assert_can_manage_institution',lambda *_:None)
    monkeypatch.setattr(tenancy,'assert_active_tenant_context',lambda *_:None)
    def rpc(name,params):
        assert name == 'b05_decide_legacy_membership'
        def execute():
            candidate = deepcopy(state)
            repeated = candidate['row']['status'] == 'approved'
            if not repeated:
                candidate['row']['status'] = 'approved'; candidate['decisions'] += 1
            if state['fault'] == 'grant':
                state['fault'] = None; raise RuntimeError('grant failed')
            grant = {'user_id':USER,'scope_id':INST,'role':'staff'}
            if grant not in candidate['grants']: candidate['grants'].append(grant)
            if state['fault'] == 'audit':
                state['fault'] = None; raise RuntimeError('audit failed')
            candidate['audits'].setdefault(INV,USER)
            candidate['fault'] = None; state.update(candidate)
            if fault == 'lost_response' and not repeated: raise TimeoutError('response lost')
            return SimpleNamespace(data={'decided':True,'audit_persisted':True,'already_applied':repeated})
        return SimpleNamespace(execute=execute)
    client.rpc.side_effect = rpc
    with pytest.raises((RuntimeError,TimeoutError)):
        tenancy.decide_membership_request(ACTOR,{},INV,ApprovalDecisionRequest(decision='approve'))
    if fault != 'lost_response':
        assert state['row']['status'] == 'pending' and state['grants'] == [existing] and not state['audits']
    for _ in range(2):
        assert tenancy.decide_membership_request(ACTOR,{},INV,ApprovalDecisionRequest(decision='approve')).status == 'approve'
    assert existing in state['grants'] and len(state['grants']) == 2
    assert state['decisions'] == 1 and len(state['audits']) == 1
    client.table.assert_not_called()


def test_sql_recovery_and_audit_bindings_are_source_checks_only():
    source = SQL.read_text(encoding='utf-8')
    recover = source.split('CREATE FUNCTION public.b05_recover_accepted_invitation',1)[1].split('$$;',1)[0]
    for predicate in ['v_inv.token_hash IS DISTINCT FROM p_digest','v_inv.acceptance_id IS NULL',
                      'v_op.kind IS DISTINCT FROM p_kind','v_op.invitation_id IS DISTINCT FROM p_id',
                      'v_op.user_id IS DISTINCT FROM v_inv.accepted_user_id','auth_user_id = v_op.auth_user_id',
                      "NOT v_op.new_account","v_op.stage NOT IN ('accepted','confirmed')"]:
        assert predicate in recover
    assert recover.count('FOR UPDATE') == 3
    assert 'INSERT INTO' not in recover and 'UPDATE public.' not in recover
    audit = source.split('CREATE FUNCTION public.b05_record_invitation_lifecycle',1)[1].split('$$;',1)[0]
    assert audit.index('INSERT INTO public.b05_invitation_lifecycle_audit') < audit.index('INSERT INTO public.platform_institution_audit_log')
    assert 'ON CONFLICT DO NOTHING' in audit and 'IF NOT FOUND THEN RETURN' in audit
    assert "WHEN p_repair THEN 'repair_actor'" in audit
    assert audit.index('IF p_repair THEN RETURN') < audit.index('INSERT INTO public.platform_institution_audit_log')
    assert 'PRIMARY KEY (kind,invitation_id,status)' in source
    assert 'trg_b05_lifecycle_audit AFTER UPDATE OF status ON public.platform_admin_invitations' in source
    assert 'trg_b05_platform_lifecycle_audit AFTER UPDATE OF status ON public.platform_super_admin_invitations' in source
    legacy = source.split('CREATE FUNCTION public.b05_decide_legacy_membership',1)[1].split('$$;',1)[0]
    assert legacy.index('FOR UPDATE') < legacy.index('UPDATE public.institution_membership_requests') < legacy.index('PERFORM public.phase81_assign_institution_role_audited') < legacy.index('INSERT INTO public.admin_audit_log')
    assert 'decided_by_user_id IS DISTINCT FROM p_actor_user_id' in legacy
    assert 'decision_reason IS DISTINCT FROM p_reason' in legacy
    assert 'DELETE' not in legacy
    assert source.rstrip().endswith('COMMIT;')


def test_expiry_candidate_rpc_is_bounded_and_can_repair_terminal_audits():
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = [{'invitation_id':INV,'status':'expired'}]
    assert repo.list_expiring_pending_invitations(client,limit=10000) == [{'invitation_id':INV,'status':'expired'}]
    client.rpc.assert_called_once_with('b05_expiry_candidates',{'p_limit':200})
    client.table.assert_not_called()
    source = SQL.read_text(encoding='utf-8').split('CREATE FUNCTION public.b05_expiry_candidates',1)[1].split('$$;',1)[0]
    assert "i.status = 'expired' AND NOT EXISTS" in source
    assert 'public.b05_invitation_lifecycle_audit' in source
    assert "to_jsonb(i) - 'token_hash'" in source


def test_stopped_successor_has_exact_post_b05_layout_and_preserves_original():
    import hashlib
    review = ROOT / 'docs/reviews/student_enrollment_final_2026-10-11'
    original = (review / 'SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql').read_bytes()
    successor = (review / 'SECURITY_CONTAINMENT_POST_B05_SUCCESSOR_DRAFT.sql').read_text(encoding='utf-8')
    assert hashlib.sha256(original).hexdigest() == '897a4c786adc487bce04462690f8a4bbcab215f2e3e53841f84a82f40c1a63c7'
    source = original.decode('utf-8')
    assert 'NOT attisdropped)<>11 THEN' in source
    assert 'NOT attisdropped)<>12 THEN' in successor
    assert "('decision_key','text')" in successor
    assert 'attnum=12 AND NOT attisdropped AND NOT attnotnull AND NOT atthasdef' in successor
    assert 'public.b05_decision_audit_key' in successor
    import re
    ledger = successor.split('FROM supabase_migrations.schema_migrations) IS DISTINCT FROM ARRAY[',1)[1].split(']::text[] THEN',1)[0]
    versions = re.findall(r"'(\d{14})'",ledger)
    assert versions == sorted(path.name.split('_',1)[0] for path in (ROOT/'supabase/migrations').glob('*.sql'))
    assert len(versions) == 40 and versions[-1] == '20261017000000'
    # Exact retained stop statements, not merely a count of RAISE EXCEPTIONs.
    stops = [line for line in source.splitlines() if line.startswith('DO $review_stop$') or line.startswith('DO $dependency_stop$')]
    assert len(stops) == 2
    for stop in stops: assert stop in successor
    assert source.rstrip().endswith('ROLLBACK;') and successor.rstrip().endswith('ROLLBACK;')


def test_legacy_routine_identities_and_authorization_are_not_replaced():
    source = SQL.read_text(encoding='utf-8')
    assert 'phase723_approve_membership_with_invitation' not in '\n'.join(
        line for line in source.splitlines() if line.startswith(('CREATE','DROP','ALTER','REVOKE','GRANT')))
    assignment = source.split('CREATE FUNCTION public.phase81_assign_institution_role_audited(',1)[1].split(') RETURNS',1)[0]
    assert 'p_actor_auth_user_id uuid' in assignment  # A distinct five-argument overload.
    assert 'DROP FUNCTION' not in source
