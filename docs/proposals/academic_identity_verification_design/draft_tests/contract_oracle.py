"""Sequential specification only: no application, SQL, network or DB simulation.

Custody methods model the separately reviewed trusted writer contract, not shipped
RPCs. Frozen records/deep copies express evidence retention only; they do not
prove database/storage immutability, authorization locks or transaction behavior.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, fields, replace
from datetime import date
import hashlib
import json

KINDS = {"official_person_key", "register_number", "university_roll_number"}
REQUIRED = ("official_person_key", "register_number")
GOVERNANCE = {"normalization", "freshness", "identifier_reuse", "authenticity",
              "locator", "retention", "assignment", "correction_review",
              "source_change", "legacy_missing_values", "lock_budget", "subject_binding", "absence_directory"}
ASCII_SPACE = " \t\r\n\f\v"
VERIFY_PERMISSION = "academic_identity.verify"


class Refused(ValueError):
    pass


class UnresolvedPolicy(Refused):
    """Missing owner decision, never an invented institutional default."""


def normalize(value, rule):
    if not isinstance(value, str) or rule not in {"exact", "ascii_trim", "ascii_trim_upper"}:
        raise Refused("policy_or_identifier")
    result = value if rule == "exact" else value.strip(ASCII_SPACE)
    if rule == "ascii_trim_upper":
        result = result.translate(str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    if not 1 <= len(result) <= 256 or not result.strip(ASCII_SPACE):
        raise Refused("policy_or_identifier")
    return result


def bounded(value, limit=2000):
    if not isinstance(value, str) or not 1 <= len(value.strip(" ")) <= limit:
        raise Refused("bounded_string")


@dataclass(frozen=True)
class Actor:
    user_id: str
    auth_id: str
    scopes: tuple[str, ...]
    role: str = "staff"
    active: bool = True
    auth_linked: bool = True
    institution_active: bool = True
    role_active: bool = True
    parent_matches: bool = True
    service_caller: bool = True
    # Deliberately ignored: role-wide/wildcard grants do not authorize.
    permissions: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Policy:
    policy_id: str
    rules: dict[str, str]
    freshness_mode: str
    max_age_seconds: int | None
    approvals: dict[str, str]
    person_key_description: str
    required: tuple[str, ...] = REQUIRED


@dataclass(frozen=True)
class Mandate:
    mandate_id: str
    institution: str
    user_id: str
    purpose: str
    owner_reference: str


@dataclass(frozen=True)
class Entry:
    entry_id: str
    source_id: str
    institution: str
    locator: str
    raw_values: dict[str, str]
    confirmation: str
    extraction_status: str = "unreviewed"


@dataclass(frozen=True)
class Source:
    source_id: str
    institution: str
    source_reference: str
    version: str | None
    as_of: str | None
    bucket: str
    object_key: str
    object_version: str
    uploaded_by: str
    uploaded_auth: str
    uploaded_at: int
    authenticity_reference: str
    import_reference: str
    issuer: str | None = None
    missing_metadata_reason: str | None = None
    authenticity_method: str = ""
    provenance_description: str = ""
    uploader_mandate_id: str = ""
    sha256: str = ""
    byte_length: int = 0
    accepted_by: str = ""
    accepted_auth: str = ""
    accepted_at: int = 0
    mandate_id: str = ""
    entry_count: int = 0


@dataclass(frozen=True)
class AccountAssociation:
    """Trusted current directory snapshot, never self-reported profile values."""
    institution: str
    person_key: str
    profile_id: str
    user_id: str
    auth_id: str
    revision: int
    active: bool = True


@dataclass(frozen=True)
class DirectoryBaseline:
    """Synthetic trusted completeness attestation, NOT inferred from local rows.

    Only fixtures populate the registry. Real directory coverage, historical
    continuity and writer appointments require owner approval and implementation.
    """
    baseline_id: str
    institution: str
    associations: tuple[AccountAssociation, ...]
    writer_user_id: str
    writer_auth_id: str
    writer_mandate_id: str
    provenance_reference: str
    observed_at: int
    complete: bool = False
    history_complete: bool = False


@dataclass(frozen=True)
class DirectoryRevision:
    institution: str
    baseline_id: str
    generation: int
    associations: tuple[AccountAssociation, ...]
    writer_user_id: str
    writer_auth_id: str
    writer_mandate_id: str
    recorded_at: int
    operation: str
    reason: str


@dataclass(frozen=True)
class BindingEvidence:
    """Synthetic receipt from a separately trusted institutional proofing writer.

    An account receipt represents validated authentication of this exact user/Auth
    pair AND independent proof that its human subject owns this official entry.
    An absence receipt represents a complete authoritative subject/account search.
    Nonempty reference strings cannot establish either fact. Only test fixtures
    populate this trusted store; no real proofing or owner approval is supplied.
    """
    evidence_id: str
    institution: str
    person_key: str
    source_id: str
    entry_id: str
    mode: str
    profile_id: str | None
    user_id: str | None
    auth_id: str | None
    association_revision: int | None
    establisher_user_id: str
    establisher_auth_id: str
    establisher_mandate_id: str
    method: str
    provenance_reference: str
    collected_at: int
    valid_until: int
    complete: bool = False
    # Separate from account association_revision, which stays NULL in no_accounts.
    directory_generation: int | None = None
    directory_baseline_id: str | None = None


@dataclass(frozen=True)
class SubjectBinding:
    binding_id: str
    evidence: BindingEvidence
    reviewer_user_id: str
    reviewer_auth_id: str
    reviewer_mandate_id: str
    approved_at: int
    policy_id: str


class Oracle:
    def __init__(self):
        self.policies = {}
        self.mandates = {}
        self.mandate_revocations = set()
        self.permission_events = {}
        self.sources = {}
        self.entries = {}
        self.invalidations = {}
        self.identities = {}
        self.claims = {}
        self.historical_owners = {}
        self.findings = []
        self.receipts = {}
        self.audit_events = []
        self.capability_active = True
        self.subject_bindings = {}
        self.binding_history = {}
        self.binding_evidence = {}
        self.binding_revocations = set()
        self.evidence_revocations = set()
        self.binding_actors = {}
        self.binding_methods = {}  # No default approved method; fixture policies only.
        self.account_associations = {}
        self.directory_baselines = {}  # Explicit upstream synthetic attestations only.
        self.directory_history = {}    # Retained tombstones/full snapshots, never reset.
        self.directory_heads = {}
        self.directory_highwater = {}  # Independent retained continuity anchor.
        self.directory_initialized = set()  # Retained bootstrap receipts, not live rows.
        self.directory_unreliable = set()  # No ordinary command clears an incident.
        self.denials = []  # Separate security-event specification, not DB audit/rollback.

    def _member(self, actor, tenant, roles=("staff", "admin")):
        if (not actor.service_caller or not actor.active or not actor.auth_linked
                or not actor.institution_active or not actor.role_active or not actor.parent_matches
                or actor.role not in roles or set(actor.scopes) != {tenant}):
            raise Refused("forbidden")

    def _mandate(self, actor, tenant, mandate_id, purpose):
        mandate = self.mandates.get(mandate_id)
        if (not mandate or mandate.institution != tenant or mandate.user_id != actor.user_id
                or mandate.purpose != purpose or not mandate.owner_reference
                or mandate_id in self.mandate_revocations):
            raise Refused("mandate")

    def _verifier(self, actor, tenant):
        self._member(actor, tenant)
        events = self.permission_events.get((tenant, actor.user_id), [])
        if not self.capability_active or not events or events[-1]["state"] != "granted":
            raise Refused("explicit_individual_permission")
        event = events[-1]
        mandate = self.mandates.get(event.get("mandate"))
        if (event.get("permission_code") != VERIFY_PERMISSION
                or event.get("institution") != tenant or event.get("target") != actor.user_id
                or event.get("actor") == actor.user_id or not event.get("auth")
                or not event.get("reason") or not isinstance(event.get("recorded_at"), int)
                or not mandate or mandate.institution != tenant
                or mandate.user_id != event.get("actor") or mandate.purpose != "permission_grantor"
                or not mandate.owner_reference):
            raise Refused("permission_provenance")

    def _policy(self, tenant, policy_id):
        versions = self.policies.get(tenant, [])
        if not versions or versions[-1].policy_id != policy_id:
            raise UnresolvedPolicy("policy_unconfigured_or_stale")
        policy = versions[-1]
        if (policy.required != REQUIRED or set(policy.rules) != KINDS
                or not GOVERNANCE <= policy.approvals.keys()
                or policy.freshness_mode not in {"bounded", "no_expiry"}
                or (policy.freshness_mode == "bounded" and
                    (policy.max_age_seconds is None or policy.max_age_seconds <= 0))
                or (policy.freshness_mode == "no_expiry" and policy.max_age_seconds is not None)
                or not policy.person_key_description):
            raise UnresolvedPolicy("policy")
        for key in GOVERNANCE:
            bounded(policy.approvals[key], 1000)
        for rule in policy.rules.values():
            normalize("probe", rule)
        if any(p.rules != policy.rules or p.person_key_description != policy.person_key_description for p in versions):
            raise Refused("collision_review")
        return policy

    def _retry(self, tenant, actor, command, request, payload):
        if not request:
            raise Refused("request")
        key = (tenant, actor.user_id, command, request)
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        previous = self.receipts.get(key)
        if previous:
            if previous[0] != encoded:
                raise Refused("idempotency_conflict")
            result = deepcopy(previous[1])
            result["replayed"] = True
            if command == "decision":
                result["head_revision"] = self.identities[result["identity_id"]]["head"]
            elif command == "permission":
                result["head_revision"] = self.permission_events[(tenant, result["target_user_id"])][-1]["revision"]
            return key, encoded, result
        return key, encoded, None

    def _save(self, key, payload, result, action):
        self.audit_events.append(deepcopy(action))
        self.receipts[key] = (payload, deepcopy(result))
        return deepcopy(result)

    def manage_permission(self, *, actor, tenant, mandate_id, target, expected,
                          request, grant, reason, policy_id=None, now=1000):
        self._member(actor, tenant, ("admin",))
        self._mandate(actor, tenant, mandate_id, "permission_grantor")
        if actor.user_id == target.user_id:
            raise Refused("self_assignment")
        if type(expected) is not int or expected < 0 or not isinstance(grant, bool):
            raise Refused("request")
        payload = dict(target=target.user_id, expected=expected, grant=grant, reason=reason,
                       mandate=mandate_id, policy=policy_id)
        key, encoded, replay = self._retry(tenant, actor, "permission", request, payload)
        if replay:
            return replay
        bounded(reason)
        history = self.permission_events.get((tenant, target.user_id), [])
        if expected != len(history):
            raise Refused("permission_revision")
        if grant:
            self._policy(tenant, policy_id)
            self._member(target, tenant)
            if not self.capability_active:
                raise Refused("explicit_individual_permission")
            if history and history[-1]["state"] == "granted":
                raise Refused("already_granted")
        elif not history or history[-1]["state"] != "granted":
            raise Refused("not_granted")
        event = dict(revision=expected+1, state="granted" if grant else "revoked",
                     actor=actor.user_id, auth=actor.auth_id, mandate=mandate_id, reason=reason,
                     permission_code=VERIFY_PERMISSION, institution=tenant, target=target.user_id,
                     target_role_snapshot=target.role if grant else None, recorded_at=now)
        self.permission_events[(tenant, target.user_id)] = history + [event]
        result = dict(event_id=f"permission-{len(self.audit_events)+1}",
                      target_user_id=target.user_id, recorded_revision=expected+1,
                      head_revision=expected+1, replayed=False)
        return self._save(key, encoded, result, ("permission", tenant, event))

    def _values(self, raw, policy):
        if not isinstance(raw, dict) or not set(REQUIRED) <= raw.keys() or not raw.keys() <= KINDS:
            raise Refused("register_number_and_person_key_required")
        return {kind: normalize(value, policy.rules[kind]) for kind, value in raw.items()}

    def accept_source(self, *, actor, tenant, mandate_id, policy_id, source, entries,
                      original_bytes, uploader, now):
        """Synthetic custody writer: hashing bytes does not prove authenticity."""
        self._member(actor, tenant)
        self._mandate(actor, tenant, mandate_id, "register_custodian")
        self._member(uploader, tenant)
        self._mandate(uploader, tenant, source.uploader_mandate_id, "register_uploader")
        if (source.uploaded_by, source.uploaded_auth) != (uploader.user_id, uploader.auth_id):
            raise Refused("uploader_identity")
        policy = self._policy(tenant, policy_id)
        if (source.institution != tenant or source.source_id in self.sources
                or source.sha256 or source.byte_length or not isinstance(original_bytes, bytes)
                or not original_bytes or not entries or source.uploaded_at > now):
            raise Refused("source")
        for value, limit in ((source.source_reference, 1000),
                             (source.bucket, 1000), (source.object_key, 1000),
                             (source.object_version, 1000), (source.uploaded_by, 256),
                             (source.uploaded_auth, 256), (source.authenticity_reference, 2000),
                             (source.import_reference, 2000), (source.authenticity_method, 1000),
                             (source.provenance_description, 2000)):
            bounded(value, limit)
        for value in (source.version, source.issuer):
            if value is not None:
                bounded(value, 256)
        if any(value is None for value in (source.version, source.as_of, source.issuer)):
            bounded(source.missing_metadata_reason)
        if source.as_of is not None:
            try:
                if len(source.as_of) != 10:
                    raise ValueError()
                date.fromisoformat(source.as_of)
            except (TypeError, ValueError):
                raise Refused("source_date") from None
        if any((s.bucket, s.object_key, s.object_version) ==
               (source.bucket, source.object_key, source.object_version) for s in self.sources.values()):
            raise Refused("object_version_reuse")
        seen_values, seen_locators, seen_ids = set(), set(), set()
        for entry in entries:
            if (entry.institution != tenant or entry.source_id != source.source_id
                    or entry.entry_id in self.entries or entry.entry_id in seen_ids):
                raise Refused("entry")
            bounded(entry.locator, 1000)
            bounded(entry.confirmation)
            if entry.extraction_status != "confirmed_original_strings":
                raise Refused("ambiguous_extraction")
            if entry.locator in seen_locators:
                raise Refused("entry_locator_duplicate")
            seen_locators.add(entry.locator)
            seen_ids.add(entry.entry_id)
            for kind, value in self._values(entry.raw_values, policy).items():
                if (kind, value) in seen_values:
                    raise Refused("ambiguous_source")
                seen_values.add((kind, value))
        accepted = replace(source, sha256=hashlib.sha256(original_bytes).hexdigest(),
                           byte_length=len(original_bytes), accepted_by=actor.user_id,
                           accepted_auth=actor.auth_id, accepted_at=now,
                           mandate_id=mandate_id, entry_count=len(entries))
        self.sources[source.source_id] = deepcopy(accepted)
        self.entries.update({e.entry_id: deepcopy(e) for e in entries})
        self.audit_events.append(("source_accept", tenant, source.source_id))
        return deepcopy(accepted)

    def invalidate_source(self, *, actor, tenant, mandate_id, source_id, reason,
                          evidence_reference, now=1000):
        self._member(actor, tenant)
        self._mandate(actor, tenant, mandate_id, "register_custodian")
        source = self.sources.get(source_id)
        if not source or source.institution != tenant or source_id in self.invalidations:
            raise Refused("source")
        bounded(reason)
        bounded(evidence_reference)
        self.invalidations[source_id] = dict(actor=actor.user_id, auth=actor.auth_id,
                                            mandate=mandate_id, reason=reason,
                                            evidence_reference=evidence_reference, recorded_at=now)
        self.audit_events.append(("source_invalidate", tenant, source_id))

    def _source_entry(self, tenant, source_id, entry_id, policy):
        source, entry = self.sources.get(source_id), self.entries.get(entry_id)
        if (not source or source.institution != tenant or source_id in self.invalidations
                or not entry or entry.source_id != source_id or entry.institution != tenant):
            raise Refused("source_or_entry")
        source_entries = [e for e in self.entries.values() if e.source_id == source_id]
        if len(source_entries) != source.entry_count:
            raise Refused("source_incomplete")
        values = self._values(entry.raw_values, policy)
        if entry.extraction_status != "confirmed_original_strings":
            raise Refused("ambiguous_extraction")
        for other in source_entries:
            if other.entry_id != entry_id and any(values.get(k) == v for k, v in self._values(other.raw_values, policy).items()):
                raise Refused("ambiguous_source")
        return source, entry, values

    def _binding_authority(self, tenant, user_id, auth_id, mandate_id, purpose):
        actor = self.binding_actors.get(user_id)
        if not actor or actor.auth_id != auth_id:
            raise Refused("binding_authority")
        self._member(actor, tenant)
        self._mandate(actor, tenant, mandate_id, purpose)

    @staticmethod
    def _directory_rows(tenant, rows):
        if not isinstance(rows, tuple):
            raise Refused("directory_snapshot")
        for row in rows:
            # Dataclass annotations/equality do not validate values. Check each
            # independent snapshot, including required fields deleted by a fault.
            if (not isinstance(row, AccountAssociation)
                    or any(field.name not in vars(row) for field in fields(AccountAssociation))
                    or row.institution != tenant
                    or type(row.revision) is not int or row.revision <= 0
                    or type(row.active) is not bool):
                raise Refused("directory_snapshot")
            try:
                for value in (row.institution, row.person_key, row.profile_id, row.user_id, row.auth_id):
                    bounded(value, 256)
            except Refused:
                raise Refused("directory_snapshot") from None
        if len({a.profile_id for a in rows}) != len(rows):
            raise Refused("directory_snapshot")
        return tuple(sorted(rows, key=lambda a: a.profile_id))

    def _live_directory_rows(self, tenant):
        """Validate the institution partition before dereferencing live records.

        Map keys locate the partition; row fields never establish their own scope.
        Faults here concern authoritative state, not a proposed writer payload.
        """
        try:
            if not isinstance(self.account_associations, dict):
                raise Refused("directory_snapshot")
            rows = []
            for key, row in self.account_associations.items():
                if not isinstance(key, tuple) or len(key) != 2:
                    raise Refused("directory_snapshot")
                for value in key:
                    bounded(value, 256)
                if key[0] != tenant:
                    continue
                self._directory_rows(tenant, (row,))
                if key[1] != row.profile_id:
                    raise Refused("directory_snapshot")
                rows.append(row)
            return self._directory_rows(tenant, tuple(rows))
        except Refused:
            self.directory_unreliable.add(tenant)
            raise

    def _directory_baseline(self, tenant, baseline_id):
        baseline = self.directory_baselines.get(baseline_id)
        try:
            self._record_shape(baseline, DirectoryBaseline, "directory_completeness_unresolved")
        except Refused:
            raise UnresolvedPolicy("directory_completeness_unresolved") from None
        for value in (baseline.baseline_id, baseline.institution, baseline.writer_user_id,
                      baseline.writer_auth_id, baseline.writer_mandate_id,
                      baseline.provenance_reference):
            bounded(value)
        if (baseline.baseline_id != baseline_id
                or baseline.institution != tenant
                or baseline.complete is not True or baseline.history_complete is not True
                or type(baseline.observed_at) is not int):
            raise UnresolvedPolicy("directory_completeness_unresolved")
        self._binding_authority(tenant, baseline.writer_user_id, baseline.writer_auth_id,
                                baseline.writer_mandate_id, "subject_directory_writer")
        self._directory_rows(tenant, baseline.associations)
        return baseline

    def initialize_directory(self, *, actor, tenant, mandate_id, baseline_id, now=1000):
        """Attribute refused bootstrap attempts; time is a synthetic trusted input."""
        try:
            return self._initialize_directory(actor=actor, tenant=tenant,
                mandate_id=mandate_id, baseline_id=baseline_id)
        except Refused as error:
            self.denials.append(dict(actor=actor.user_id, auth=actor.auth_id, institution=tenant,
                operation="directory_initialize", baseline_id=baseline_id,
                code=str(error), observed_at=now))
            raise

    def _initialize_directory(self, *, actor, tenant, mandate_id, baseline_id):
        """Trusted bootstrap specification; an empty dict/reference is NOT proof.

        No reset/rebootstrap is permitted. A real trusted attestation and durable
        baseline/highwater recovery protocol do not exist in this package.
        """
        self._binding_authority(tenant, actor.user_id, actor.auth_id, mandate_id,
                                "subject_directory_writer")
        self._member(actor, tenant)
        baseline = self._directory_baseline(tenant, baseline_id)
        if (actor.user_id, actor.auth_id, mandate_id) != (
                baseline.writer_user_id, baseline.writer_auth_id, baseline.writer_mandate_id):
            raise Refused("directory_authority")
        if (tenant in self.directory_history or tenant in self.directory_heads
                or tenant in self.directory_highwater or tenant in self.directory_unreliable
                or any(t == tenant for t, _ in self.directory_initialized)):
            raise Refused("directory_reset_forbidden")
        rows = self._directory_rows(tenant, baseline.associations)
        live = self._live_directory_rows(tenant)
        if rows != live:
            raise Refused("directory_snapshot")
        head = DirectoryRevision(tenant, baseline_id, 1, rows, actor.user_id, actor.auth_id,
            mandate_id, baseline.observed_at, "baseline", "Synthetic attested complete baseline")
        self.directory_history[tenant] = (head,)
        self.directory_heads[tenant] = head
        self.directory_highwater[tenant] = 1
        self.directory_initialized.add((tenant, baseline_id))
        self.audit_events.append(("directory_baseline", tenant, asdict(head)))
        return deepcopy(head)

    def _directory_state(self, tenant):
        try:
            return self._checked_directory_state(tenant)
        except Refused:
            # An observed integrity/completeness loss cannot heal by deleting rows
            # or restoring an old checkpoint. This security latch changes no
            # decision/history/claims and has no ordinary clear command.
            self.directory_unreliable.add(tenant)
            raise

    def _checked_directory_state(self, tenant):
        history, head = self.directory_history.get(tenant), self.directory_heads.get(tenant)
        highwater = self.directory_highwater.get(tenant)
        if (tenant in self.directory_unreliable or not isinstance(history, tuple) or not history
                or not isinstance(head, DirectoryRevision)
                or any(field.name not in vars(head) for field in fields(DirectoryRevision))
                # Validate the separate head BEFORE equality: True == 1 and
                # 1.0 == 1 must never authenticate malformed state.
                or type(head.generation) is not int or head.generation <= 0
                or type(head.recorded_at) is not int
                or type(highwater) is not int
                or highwater <= 0 or len(history) != highwater or head.generation != highwater):
            raise UnresolvedPolicy("directory_history_unreliable")
        # A valid journal/live tuple cannot authenticate an unchecked head tuple:
        # e.g. a head association revision of True compares equal to retained 1.
        self._directory_rows(tenant, head.associations)
        for value in (head.institution, head.baseline_id, head.writer_user_id,
                      head.writer_auth_id, head.writer_mandate_id, head.operation, head.reason):
            bounded(value)
        if (tenant, head.baseline_id) not in self.directory_initialized:
            raise UnresolvedPolicy("directory_history_unreliable")
        baseline = self._directory_baseline(tenant, head.baseline_id)
        prior_time = baseline.observed_at
        for generation, event in enumerate(history, 1):
            if (not isinstance(event, DirectoryRevision)
                    or any(field.name not in vars(event) for field in fields(DirectoryRevision))):
                raise UnresolvedPolicy("directory_history_unreliable")
            self._directory_rows(tenant, event.associations)
            if (type(event.generation) is not int
                    or event.generation <= 0
                    or event.generation != generation or event.institution != tenant
                    or event.baseline_id != baseline.baseline_id
                    or type(event.recorded_at) is not int or event.recorded_at < prior_time
                    or (generation == 1 and (event.operation != "baseline"
                        or event.recorded_at != baseline.observed_at
                        or event.associations != self._directory_rows(tenant, baseline.associations)))):
                raise UnresolvedPolicy("directory_history_unreliable")
            prior_time = event.recorded_at
        if history[-1] != head:
            raise UnresolvedPolicy("directory_history_unreliable")
        self._binding_authority(tenant, head.writer_user_id, head.writer_auth_id,
                                head.writer_mandate_id, "subject_directory_writer")
        live = self._live_directory_rows(tenant)
        if live != head.associations:
            raise UnresolvedPolicy("directory_snapshot_untracked")
        return head

    def record_directory_change(self, *, actor, tenant, mandate_id, expected_generation,
                                associations, operation, reason, now):
        """Sequential proposed trusted writer, not an application/SQL endpoint.

        The institution-wide generation advances even for equal before/after
        values (e.g. recovery). Deletions retain prior snapshots as tombstones.
        All actual writers, including recovery/restore, must participate atomically.
        """
        try:
            self._binding_authority(tenant, actor.user_id, actor.auth_id, mandate_id,
                                    "subject_directory_writer")
            self._member(actor, tenant)
            head = self._directory_state(tenant)
            if (type(expected_generation) is not int or expected_generation <= 0
                    or expected_generation != head.generation):
                raise Refused("directory_revision_conflict")
            if (operation not in {"create", "remove", "reassociate", "recover", "replace", "activate", "deactivate", "restore"}
                    or type(now) is not int or now < head.recorded_at):
                raise Refused("directory_change")
            bounded(reason)
            rows = self._directory_rows(tenant, associations)
            for row in rows:
                prior = next((a for a in head.associations if a.profile_id == row.profile_id), None)
                if row != prior or operation in {"recover", "replace", "restore"}:
                    known_revisions = [a.revision for event in self.directory_history[tenant]
                        for a in event.associations if a.profile_id == row.profile_id
                        or a.person_key == row.person_key or a.user_id == row.user_id or a.auth_id == row.auth_id]
                    if row.revision <= max(known_revisions, default=0):
                        raise Refused("directory_association_revision")
            event = DirectoryRevision(tenant, head.baseline_id, head.generation + 1, rows,
                actor.user_id, actor.auth_id, mandate_id, now, operation, reason)
            # All checks precede this sequential transition; not DB atomicity proof.
            self.account_associations = {k: a for k, a in self.account_associations.items()
                                         if k[0] != tenant}
            self.account_associations.update({(tenant, a.profile_id): a for a in rows})
            self.directory_history[tenant] += (event,)
            self.directory_heads[tenant] = event
            self.directory_highwater[tenant] = event.generation
            self.audit_events.append(("directory_change", tenant, asdict(event)))
            return deepcopy(event)
        except Refused as error:
            self.denials.append(dict(actor=actor.user_id, auth=actor.auth_id, institution=tenant,
                operation="directory_change", code=str(error), observed_at=now))
            raise

    def _absence_generation(self, receipt, tenant):
        head = self._directory_state(tenant)
        if (type(receipt.directory_generation) is not int
                or receipt.directory_generation <= 0
                or receipt.directory_generation != head.generation
                or receipt.directory_baseline_id != head.baseline_id
                or head.recorded_at > receipt.collected_at):
            raise Refused("absence_directory_changed")
        return head

    @staticmethod
    def _record_shape(record, kind, code):
        # Defaults and dataclass equality cannot authenticate a missing field.
        if type(record) is not kind or set(vars(record)) != {f.name for f in fields(kind)}:
            raise Refused(code)

    @classmethod
    def _evidence_schema(cls, receipt):
        """Pure structural validation, including copies not selected as current.

        No directory access/incident marking or current authority/expiry check:
        old evidence remains historical, even after source/policy replacement.
        """
        cls._record_shape(receipt, BindingEvidence, "binding_incomplete")
        for value in (receipt.evidence_id, receipt.source_id, receipt.entry_id,
                      receipt.method, receipt.provenance_reference):
            bounded(value)
        for value in (receipt.institution, receipt.person_key, receipt.establisher_user_id,
                      receipt.establisher_auth_id, receipt.establisher_mandate_id):
            bounded(value, 256)
        if (not isinstance(receipt.mode, str) or receipt.mode not in {"account", "no_accounts"}
                or receipt.complete is not True
                or type(receipt.collected_at) is not int or type(receipt.valid_until) is not int
                or receipt.collected_at >= receipt.valid_until):
            raise Refused("binding_evidence_unusable")
        account_fields = (receipt.profile_id, receipt.user_id, receipt.auth_id, receipt.association_revision)
        if receipt.mode == "account":
            for value in account_fields[:3]:
                bounded(value, 256)
            if type(receipt.association_revision) is not int or receipt.association_revision <= 0:
                raise Refused("binding_incomplete")
        elif any(value is not None for value in account_fields):
            raise Refused("binding_contradiction")
        if receipt.mode == "no_accounts" or receipt.directory_generation is not None:
            if type(receipt.directory_generation) is not int or receipt.directory_generation <= 0:
                raise Refused("absence_directory_changed")
        if receipt.mode == "no_accounts" or receipt.directory_baseline_id is not None:
            try:
                bounded(receipt.directory_baseline_id)
            except Refused:
                raise Refused("absence_directory_changed") from None

    @classmethod
    def _binding_schema(cls, binding):
        cls._record_shape(binding, SubjectBinding, "subject_binding_unresolved")
        for value in (binding.binding_id, binding.reviewer_user_id, binding.reviewer_auth_id,
                      binding.reviewer_mandate_id, binding.policy_id):
            bounded(value)
        cls._evidence_schema(binding.evidence)
        if (type(binding.approved_at) is not int
                or not binding.evidence.collected_at <= binding.approved_at < binding.evidence.valid_until):
            raise Refused("binding_evidence_unusable")

    @classmethod
    def _historical_binding(cls, decision):
        """Validate the full serialized approval and proof before tuple/dict equality."""
        try:
            evidence = decision.get("evidence")
            if not isinstance(evidence, dict):
                raise Refused("historical_binding_unresolved")
            snapshot = evidence.get("subject_binding")
            if (not isinstance(snapshot, dict)
                    or set(snapshot) != {f.name for f in fields(SubjectBinding)}):
                raise Refused("historical_binding_unresolved")
            receipt = snapshot["evidence"]
            if (not isinstance(receipt, dict)
                    or set(receipt) != {f.name for f in fields(BindingEvidence)}):
                raise Refused("historical_binding_unresolved")
            binding = SubjectBinding(**dict(snapshot, evidence=BindingEvidence(**receipt)))
            cls._binding_schema(binding)
            return binding
        except Refused:
            raise Refused("historical_binding_unresolved") from None

    def _binding_receipt(self, binding, tenant, now):
        self._binding_schema(binding)
        receipt = binding.evidence
        retained = self.binding_evidence.get(receipt.evidence_id)
        self._evidence_schema(retained)
        if (retained != receipt
                or receipt.evidence_id in self.evidence_revocations
                or binding.binding_id in self.binding_revocations
                or receipt.institution != tenant or receipt.complete is not True
                or receipt.mode not in {"account", "no_accounts"}
                or (receipt.method, receipt.mode) not in self.binding_methods.get(tenant, ())
                or not all(type(t) is int for t in
                           (receipt.collected_at, binding.approved_at, receipt.valid_until, now))
                or not receipt.collected_at <= binding.approved_at <= now < receipt.valid_until):
            raise Refused("binding_evidence_unusable")
        self._policy(tenant, binding.policy_id)
        for value in (binding.binding_id, receipt.evidence_id, receipt.person_key,
                      receipt.source_id, receipt.entry_id, receipt.provenance_reference):
            bounded(value)
        self._binding_authority(tenant, receipt.establisher_user_id, receipt.establisher_auth_id,
                                receipt.establisher_mandate_id, "subject_binding_establisher")
        self._binding_authority(tenant, binding.reviewer_user_id, binding.reviewer_auth_id,
                                binding.reviewer_mandate_id, "subject_binding_reviewer")
        if (binding.reviewer_user_id in {receipt.establisher_user_id, receipt.user_id}
                or binding.reviewer_auth_id in {receipt.establisher_auth_id, receipt.auth_id}
                or receipt.establisher_user_id == receipt.user_id
                or receipt.establisher_auth_id == receipt.auth_id):
            raise Refused("self_approval")
        source, entry = self.sources.get(receipt.source_id), self.entries.get(receipt.entry_id)
        if (not source or source.institution != tenant or receipt.source_id in self.invalidations
                or not entry or entry.source_id != receipt.source_id or entry.institution != tenant
                or source.accepted_at > receipt.collected_at):
            raise Refused("binding_source")
        if receipt.mode == "no_accounts":
            self._absence_generation(receipt, tenant)
        return receipt

    def approve_binding(self, *, actor, tenant, mandate_id, binding_id, evidence_id, policy_id, now):
        """Sequential trusted approval specification, NOT an implemented RPC."""
        try:
            return self._approve_binding(actor=actor, tenant=tenant, mandate_id=mandate_id,
                binding_id=binding_id, evidence_id=evidence_id, policy_id=policy_id, now=now)
        except Refused as error:
            self.denials.append(dict(actor=actor.user_id, auth=actor.auth_id, institution=tenant,
                operation="approve_binding", binding_id=binding_id, evidence_id=evidence_id,
                code=str(error), observed_at=now))
            raise

    def _approve_binding(self, *, actor, tenant, mandate_id, binding_id, evidence_id, policy_id, now):
        self._member(actor, tenant)
        self._mandate(actor, tenant, mandate_id, "subject_binding_reviewer")
        policy = self._policy(tenant, policy_id)
        receipt = self.binding_evidence.get(evidence_id)
        if not receipt or binding_id in self.binding_history:
            raise Refused("binding_evidence_unusable")
        binding = SubjectBinding(binding_id, deepcopy(receipt), actor.user_id, actor.auth_id, mandate_id, now, policy_id)
        self._binding_receipt(binding, tenant, now)
        if self._values(self.entries[receipt.entry_id].raw_values, policy)["official_person_key"] != receipt.person_key:
            raise Refused("binding_subject")
        self.binding_history[binding_id] = deepcopy(binding)
        self.subject_bindings[(tenant, receipt.person_key)] = deepcopy(binding)
        self.audit_events.append(("binding_approval", tenant, asdict(binding)))
        return deepcopy(binding)

    @staticmethod
    def _association_tuple(receipt):
        return tuple(getattr(receipt, k) for k in
                     ("institution", "person_key", "mode", "profile_id", "user_id", "auth_id", "association_revision"))

    @staticmethod
    def _account_profile(tenant, target, students):
        """Validate supplied profile snapshots without declaring a directory fault."""
        try:
            bounded(target, 256)
            if not isinstance(students, (tuple, list)):
                raise Refused("binding_profile")
            rows = []
            for row in students:
                if not isinstance(row, dict):
                    raise Refused("binding_profile")
                for field in ("institution_id", "student_id"):
                    bounded(row.get(field), 256)
                if row["institution_id"] == tenant and row["student_id"] == target:
                    for field in ("user_id", "auth_user_id"):
                        bounded(row.get(field), 256)
                    revision = row.get("association_revision")
                    if type(revision) is not int or revision <= 0:
                        raise Refused("binding_profile")
                    rows.append(row)
            if len(rows) != 1:
                raise Refused("binding_profile")
            return rows[0]
        except Refused:
            raise Refused("binding_profile") from None

    def _independent_subject(self, actor, tenant, values, target, students, source_id, entry_id, now):
        binding = self.subject_bindings.get((tenant, values["official_person_key"]))
        receipt = self._binding_receipt(binding, tenant, now)
        retained = self.binding_history.get(binding.binding_id)
        self._binding_schema(retained)
        if (retained != binding
                or receipt.person_key != values["official_person_key"]
                or (receipt.source_id, receipt.entry_id) != (source_id, entry_id)):
            raise Refused("binding_subject_or_version")
        if (actor.user_id in {receipt.user_id, binding.reviewer_user_id, receipt.establisher_user_id}
                or actor.auth_id in {receipt.auth_id, binding.reviewer_auth_id, receipt.establisher_auth_id}):
            raise Refused("self_approval")
        # Absence receipts already checked this state in _binding_receipt.
        # Account mode must independently take the same strict integrity path.
        head = (self._directory_state(tenant) if receipt.mode == "account"
                else self.directory_heads[tenant])
        directory = head.associations
        related = [a for a in directory if a.person_key == receipt.person_key]
        if receipt.mode == "no_accounts":
            if target is not None or related:
                raise Refused("binding_no_accounts")
            if any(a.person_key == receipt.person_key for event in self.directory_history[tenant]
                   for a in event.associations):
                # A new receipt cannot decide previously-associated-subject policy.
                raise UnresolvedPolicy("absence_history_requires_review")
        else:
            row = self._account_profile(tenant, target, students)
            if row.get("user_id") == actor.user_id or row.get("auth_user_id") == actor.auth_id:
                raise Refused("self_approval")
            expected = AccountAssociation(tenant, receipt.person_key, receipt.profile_id,
                                          receipt.user_id, receipt.auth_id, receipt.association_revision)
            overlapping = [a for a in directory if a.profile_id == receipt.profile_id
                           or a.user_id == receipt.user_id or a.auth_id == receipt.auth_id]
            if (target != receipt.profile_id or related != [expected]
                    or overlapping != [expected]
                    or self.account_associations.get((tenant, target)) != expected
                    or (row.get("user_id"), row.get("auth_user_id"), row.get("association_revision"))
                    != (receipt.user_id, receipt.auth_id, receipt.association_revision)):
                raise Refused("binding_account_ownership")
        return binding

    def _compare(self, tenant, values, policy, target, students, rosters):
        matched, observed_students, observed_rosters = [], [], []
        def local_rows(rows, code, *, profiles=False):
            if not isinstance(rows, (tuple, list)):
                raise Refused(code)
            for row in rows:
                if not isinstance(row, dict):
                    raise Refused(code)
                bounded(row.get("institution_id"), 256)
                if row["institution_id"] == tenant:
                    if profiles:
                        bounded(row.get("student_id"), 256)
                    for kind in ("register_number", "university_roll_number"):
                        raw = row.get(kind)
                        if raw is not None and not isinstance(raw, str):
                            raise Refused(code)
            return rows
        students = local_rows(students, "binding_profile", profiles=True)
        rosters = local_rows(rosters, "roster_conflict")
        for candidate in students:
            if candidate["institution_id"] != tenant:
                continue
            comparisons = []
            for kind in ("register_number", "university_roll_number"):
                raw = candidate.get(kind)
                if raw is not None and raw.strip(ASCII_SPACE):
                    comparisons.append(normalize(raw, policy.rules[kind]) == values.get(kind))
            if any(comparisons):
                if (not all(comparisons) or not candidate.get("register_number")
                        or normalize(candidate["register_number"], policy.rules["register_number"]) != values["register_number"]):
                    raise Refused("identity_conflict")
                matched.append(candidate["student_id"])
                observed_students.append({k: candidate.get(k) for k in
                    ("student_id", "register_number", "university_roll_number", "user_id", "auth_user_id", "association_revision")})
        if len(matched) > 1 or (target and target not in matched) or (len(matched) == 1 and target != matched[0]):
            raise Refused("link_conflict")
        for roster in rosters:
            if roster["institution_id"] != tenant:
                continue
            comparisons = [normalize(roster[k], policy.rules[k]) == values.get(k)
                           for k in ("register_number", "university_roll_number")
                           if roster.get(k) and roster[k].strip(ASCII_SPACE)]
            if any(comparisons):
                if (not all(comparisons) or not roster.get("register_number")
                        or normalize(roster["register_number"], policy.rules["register_number"]) != values["register_number"]
                        or (roster.get("linked_student_id") and roster["linked_student_id"] != target)):
                    raise Refused("roster_conflict")
                observed_rosters.append({k: roster.get(k) for k in
                    ("roster_id", "section_id", "register_number",
                     "university_roll_number", "linked_student_id")})
        return observed_students, observed_rosters

    def decide(self, *, actor, tenant, identity, expected, request, operation, reason,
               policy_id=None, source_id=None, entry_id=None, student=None,
               students=(), rosters=(), now=1000):
        try:
            return self._decide(actor=actor, tenant=tenant, identity=identity, expected=expected,
                request=request, operation=operation, reason=reason, policy_id=policy_id,
                source_id=source_id, entry_id=entry_id, student=student,
                students=deepcopy(students), rosters=deepcopy(rosters), now=now)
        except Refused as error:
            self.denials.append(dict(actor=actor.user_id, auth=actor.auth_id, institution=tenant,
                                     identity=identity, operation=operation, request=request,
                                     code=str(error), observed_at=now))
            raise

    def _decide(self, *, actor, tenant, identity, expected, request, operation, reason,
                policy_id=None, source_id=None, entry_id=None, student=None,
                students=(), rosters=(), now=1000):
        self._verifier(actor, tenant)
        if (type(expected) is not int or expected < 0 or not isinstance(operation, str)
                or operation not in {"verify", "reverify", "correct", "withdraw"}):
            raise Refused("request")
        if student is not None:
            try:
                bounded(student, 256)
            except Refused:
                raise Refused("binding_profile") from None
        payload = dict(identity=identity, expected=expected, operation=operation, reason=reason,
                       policy=policy_id, source=source_id, entry=entry_id, student=student)
        key, encoded, replay = self._retry(tenant, actor, "decision", request, payload)
        if replay:
            return replay
        bounded(reason)
        state = self.identities.get(identity)
        if ((not state and (expected != 0 or operation != "verify"))
                or (state and (state["institution"] != tenant or state["head"] != expected or operation == "verify"))):
            raise Refused("revision_or_resource")
        history = state["history"] if state else []
        prior = history[-1] if history else None
        target = state["student"] if state else None
        values, until = {}, None
        if operation == "withdraw":
            if not prior or prior["decision"] != "verified":
                raise Refused("not_currently_positive")
            if any(v is not None for v in (policy_id, source_id, entry_id, student)):
                raise Refused("withdrawal_input")
            evidence = dict(withdraws=prior["revision"], prior_evidence=deepcopy(prior["evidence"]))
            effective_policy, effective_source, effective_entry = prior["policy"], prior["source"], prior["entry"]
        else:
            policy = self._policy(tenant, policy_id)
            source, entry, values = self._source_entry(tenant, source_id, entry_id, policy)
            if any(d["decision"] == "verified" and d["values"]["official_person_key"] != values["official_person_key"] for d in history):
                raise Refused("reassociation")
            if operation == "reverify" and (not prior or prior["decision"] != "verified" or prior["values"] != values or (student is not None and student != target)):
                raise Refused("correction_required")
            if target is not None and student is not None and target != student:
                raise Refused("reassociation")
            target = target if target is not None else student
            for kind, value in values.items():
                claim = (tenant, kind, value)
                if self.claims.get(claim, identity) != identity:
                    raise Refused("identity_conflict")
                if self.historical_owners.get(claim, identity) != identity:
                    raise UnresolvedPolicy("identity_conflict: identifier_reuse_unresolved")
            binding = self._independent_subject(actor, tenant, values, target, students, source_id, entry_id, now)
            # Ordinary commands cannot migrate a historical positive to another
            # account, Auth identity, profile or association revision (even NULL
            # to account). Recovery/reassociation needs a separate owner design.
            for old in history:
                if old["decision"] == "verified":
                    old_receipt = self._historical_binding(old).evidence
                    if self._association_tuple(old_receipt) != self._association_tuple(binding.evidence):
                        raise UnresolvedPolicy("account_reassociation_unresolved")
            if target is not None and any(s["institution"] == tenant and s["student"] == target and other != identity for other, s in self.identities.items()):
                raise Refused("profile_conflict")
            observed_students, observed_rosters = self._compare(tenant, values, policy, target, students, rosters)
            evidence = dict(source_manifest=asdict(source), entry_locator=entry.locator,
                            raw_values=deepcopy(entry.raw_values), checked_identifiers=sorted(entry.raw_values),
                            observed_students=observed_students, observed_rosters=observed_rosters,
                            subject_binding=asdict(binding))
            until = now + policy.max_age_seconds if policy.freshness_mode == "bounded" else None
            effective_policy, effective_source, effective_entry = policy_id, source_id, entry_id
        # Sequential state transition only; NO simulated transaction/rollback/locks.
        rev = expected + 1
        decision = dict(revision=rev, supersedes=expected or None, operation=operation,
                        decision="withdrawn" if operation == "withdraw" else "verified",
                        values=deepcopy(values), evidence=deepcopy(evidence), student=target,
                        verifier=actor.user_id, auth=actor.auth_id, reason=reason,
                        policy=effective_policy, source=effective_source, entry=effective_entry,
                        verifier_permission_event=deepcopy(self.permission_events[(tenant, actor.user_id)][-1]),
                        decided_at=now, valid_until=until)
        self.identities[identity] = dict(institution=tenant, head=rev, student=target, history=history+[decision])
        self.claims = {k: v for k, v in self.claims.items() if v != identity}
        for kind, value in values.items():
            self.claims[(tenant, kind, value)] = identity
            self.historical_owners[(tenant, kind, value)] = identity
        result = dict(identity_id=identity, decision_id=f"{identity}:{rev}", recorded_revision=rev,
                      recorded_decision=decision["decision"], head_revision=rev, replayed=False)
        return self._save(key, encoded, result, ("decision", tenant, identity, rev))

    def finding(self, *, actor, tenant, request, source_id, locator, finding,
                observed, reason, entry_id=None, candidate=None, context=None, students=(), now=1000):
        self._verifier(actor, tenant)
        payload = dict(source=source_id, locator=locator, finding=finding, observed=observed,
                       reason=reason, entry=entry_id, student=candidate, identity=context)
        key, encoded, replay = self._retry(tenant, actor, "finding", request, payload)
        if replay:
            return replay
        bounded(reason)
        bounded(locator, 1000)
        if finding not in {"rejected_match", "unresolved"} or not isinstance(observed, dict):
            raise Refused("finding")
        for kind, value in observed.items():
            if kind not in {"register_number", "university_roll_number"} or not isinstance(value, str) or not 1 <= len(value) <= 256:
                raise Refused("finding")
        if len(json.dumps(observed).encode()) > 16384:
            raise Refused("finding")
        source, entry = self.sources.get(source_id), self.entries.get(entry_id)
        if not source or source.institution != tenant or source_id in self.invalidations:
            raise Refused("source")
        if entry_id and (not entry or entry.source_id != source_id or entry.institution != tenant or entry.locator != locator):
            raise Refused("entry")
        if candidate and not any(s["student_id"] == candidate and s["institution_id"] == tenant for s in students):
            raise Refused("candidate")
        if context and (context not in self.identities or self.identities[context]["institution"] != tenant):
            raise Refused("context")
        record = dict(payload, institution=tenant, verifier=actor.user_id, auth=actor.auth_id,
                      recorded_at=now,
                      verifier_permission_event=deepcopy(self.permission_events[(tenant, actor.user_id)][-1]))
        self.findings.append(deepcopy(record))
        result = dict(finding_id=f"finding-{len(self.findings)}", finding=finding, replayed=False)
        return self._save(key, encoded, result, ("finding", tenant, record))

    def current_usable(self, tenant, identity, policy_id, *, now, students=(), rosters=()):
        """Specification of a FUTURE projection, never an invitation capability."""
        state = self.identities.get(identity)
        if not state or state["institution"] != tenant:
            return False
        head = state["history"][-1]
        if head["decision"] != "verified" or head["source"] in self.invalidations:
            return False
        try:
            policy = self._policy(tenant, policy_id)
            # No invented inheritance rule for changed freshness/source policy.
            if head["policy"] != policy_id:
                return False
            _, _, values = self._source_entry(tenant, head["source"], head["entry"], policy)
            if values != head["values"]:
                return False
            recorded_actor = Actor(head["verifier"], head["auth"], (tenant,))
            binding = self._independent_subject(recorded_actor, tenant, values, state["student"],
                                                students, head["source"], head["entry"], now)
            for old in state["history"]:
                if old["decision"] == "verified":
                    historical = self._historical_binding(old)
                    if self._association_tuple(historical.evidence) != self._association_tuple(binding.evidence):
                        return False
            if binding != self._historical_binding(head):
                return False  # New approval never silently refreshes an old decision.
            self._compare(tenant, head["values"], self.policies[tenant][-1], state["student"], students, rosters)
        except Refused:
            return False
        return head["valid_until"] is None or now < head["valid_until"]

