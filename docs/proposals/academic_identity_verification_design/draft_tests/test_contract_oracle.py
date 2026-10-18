"""Offline specification tests only; no SQL parser, DB, application or network."""
from copy import deepcopy
from dataclasses import is_dataclass, replace
from pathlib import Path
import hashlib
import re
import unittest

from contract_oracle import (AccountAssociation, Actor, BindingEvidence, DirectoryBaseline, Entry, GOVERNANCE, Mandate, Oracle, Policy,
                             Refused, Source, SubjectBinding, UnresolvedPolicy, normalize)


def install_binding(e, *, account=False, source_id=None, entry_id=None, person_key="person-1",
                    profile_id="s1", user_id="subject-user", auth_id="subject-auth", revision=None,
                    valid_until=10**12, collected_at=40, approved_at=50):
    """Explicit synthetic institutional proofing receipt and separate approval.

    Profile construction NEVER creates ownership evidence. These trusted fixture
    records stand in for the unimplemented owner-approved proofing workflow.
    """
    o, tenant = e["o"], e["tenant"]
    if account:
        if revision is None:
            current = o.account_associations.get((tenant, profile_id))
            if current and (current.person_key, current.user_id, current.auth_id, current.active) == (
                    person_key, user_id, auth_id, True):
                revision = current.revision
            else:
                # Only positive fixture setup chooses a fresh trusted revision.
                # Adversarial directory tests pass explicit revisions to the writer.
                known = [a.revision for event in o.directory_history[tenant] for a in event.associations
                         if a.profile_id == profile_id or a.person_key == person_key
                         or a.user_id == user_id or a.auth_id == auth_id]
                revision = max(known, default=0) + 1
        association = AccountAssociation(
            tenant, person_key, profile_id, user_id, auth_id, revision)
        rows = tuple(a for a in o.account_associations.values()
                     if a.institution == tenant and a.profile_id != profile_id) + (association,)
        o.record_directory_change(actor=e["directory_writer"], tenant=tenant,
            mandate_id=e["directory_mandate"].mandate_id,
            expected_generation=o.directory_heads[tenant].generation, associations=rows,
            operation="create", reason="Synthetic explicit account directory update", now=30)
    seq = len(o.binding_evidence) + 1
    evidence = BindingEvidence(f"proof:{tenant}:{seq}", tenant, person_key,
        source_id or e["source"].source_id, entry_id or e["entry"].entry_id,
        "account" if account else "no_accounts", profile_id if account else None,
        user_id if account else None, auth_id if account else None, revision if account else None,
        e["establisher"].user_id, e["establisher"].auth_id, e["establish_mandate"].mandate_id,
        "synthetic-proofing", "Synthetic private inspected proofing/search receipt",
        collected_at, valid_until, True,
        o.directory_heads[tenant].generation if not account else None,
        o.directory_heads[tenant].baseline_id if not account else None)
    o.binding_evidence[evidence.evidence_id] = evidence
    return o.approve_binding(actor=e["reviewer"], tenant=tenant,
        mandate_id=e["review_mandate"].mandate_id, binding_id=f"binding:{tenant}:{seq}",
        evidence_id=evidence.evidence_id, policy_id=e["policy"].policy_id, now=approved_at)


def fixture(*, roll=True, tenant="institution-a", oracle=None, account=False):
    """Every value/policy/approval here is synthetic, never institutional policy."""
    o = oracle or Oracle()
    staff = Actor(f"staff:{tenant}", f"auth-staff:{tenant}", (tenant,))
    admin = Actor(f"admin:{tenant}", f"auth-admin:{tenant}", (tenant,), role="admin")
    grantor = Actor(f"grantor:{tenant}", f"auth-grantor:{tenant}", (tenant,), role="admin")
    custodian = Actor(f"custodian:{tenant}", f"auth-custodian:{tenant}", (tenant,))
    uploader = Actor(f"uploader:{tenant}", f"auth-uploader:{tenant}", (tenant,))
    establisher = Actor(f"establisher:{tenant}", f"auth-establisher:{tenant}", (tenant,))
    reviewer = Actor(f"reviewer:{tenant}", f"auth-reviewer:{tenant}", (tenant,))
    directory_writer = Actor(f"directory-writer:{tenant}", f"auth-directory:{tenant}", (tenant,))
    policy = Policy(f"policy:{tenant}", {k: "ascii_trim" for k in
                    ("official_person_key", "register_number", "university_roll_number")},
                    "bounded", 3600, {k: f"synthetic-approval:{k}" for k in GOVERNANCE},
                    "Synthetic stable source person key")
    o.policies[tenant] = [policy]
    grant_mandate = Mandate(f"grant-mandate:{tenant}", tenant, grantor.user_id,
                           "permission_grantor", "synthetic-owner")
    custody_mandate = Mandate(f"custody-mandate:{tenant}", tenant, custodian.user_id,
                             "register_custodian", "synthetic-owner")
    upload_mandate = Mandate(f"upload-mandate:{tenant}", tenant, uploader.user_id,
                            "register_uploader", "synthetic-owner")
    establish_mandate = Mandate(f"establish-mandate:{tenant}", tenant, establisher.user_id,
                               "subject_binding_establisher", "synthetic-owner")
    review_mandate = Mandate(f"review-mandate:{tenant}", tenant, reviewer.user_id,
                            "subject_binding_reviewer", "synthetic-owner")
    directory_mandate = Mandate(f"directory-mandate:{tenant}", tenant, directory_writer.user_id,
                               "subject_directory_writer", "synthetic-owner")
    o.mandates.update({m.mandate_id: m for m in
                     (grant_mandate, custody_mandate, upload_mandate, establish_mandate, review_mandate, directory_mandate)})
    o.binding_actors.update({a.user_id: a for a in (establisher, reviewer, directory_writer)})
    baseline = DirectoryBaseline(f"directory-baseline:{tenant}", tenant, (),
        directory_writer.user_id, directory_writer.auth_id, directory_mandate.mandate_id,
        "Synthetic upstream inspected completeness/history attestation; NOT real proof", 25, True, True)
    o.directory_baselines[baseline.baseline_id] = baseline
    o.initialize_directory(actor=directory_writer, tenant=tenant,
        mandate_id=directory_mandate.mandate_id, baseline_id=baseline.baseline_id)
    o.binding_methods[tenant] = frozenset({("synthetic-proofing", "account"), ("synthetic-proofing", "no_accounts")})
    source = Source(f"source:{tenant}", tenant, "synthetic-register", "fixture-v1", "2026-01-02",
                    "synthetic-private", f"{tenant}/register/fixture-v1", "object-version-1",
                    uploader.user_id, uploader.auth_id, 10,
                    "synthetic-authenticity-attestation", "synthetic-entry-confirmation",
                    issuer="Synthetic registrar", authenticity_method="synthetic documented handoff",
                    provenance_description="Synthetic registrar delivery independently confirmed by custodian",
                    uploader_mandate_id=upload_mandate.mandate_id)
    raw = {"official_person_key": "person-1", "register_number": " 0012 "}
    if roll:
        raw["university_roll_number"] = "roll-1"
    entry = Entry(f"entry:{tenant}", source.source_id, tenant, "Sheet1!A2:C2", raw,
                  "synthetic-confirmation", "confirmed_original_strings")
    data = b"synthetic original bytes; register=0012; person=person-1"
    accepted = o.accept_source(actor=custodian, tenant=tenant, mandate_id=custody_mandate.mandate_id,
                               policy_id=policy.policy_id, source=source, entries=[entry], original_bytes=data,
                               uploader=uploader, now=20)
    for index, target in enumerate((staff, admin)):
        o.manage_permission(actor=grantor, tenant=tenant, mandate_id=grant_mandate.mandate_id,
                            target=target, expected=0, request=f"setup-grant-{index}",
                            grant=True, reason="Synthetic explicit assignment", policy_id=policy.policy_id)
    args = dict(actor=staff, tenant=tenant, identity=f"identity:{tenant}", expected=0,
                request="verify-1", operation="verify", reason="Synthetic independent check",
                policy_id=policy.policy_id, source_id=source.source_id, entry_id=entry.entry_id)
    e = dict(o=o, staff=staff, admin=admin, grantor=grantor, custodian=custodian,
                uploader=uploader, upload_mandate=upload_mandate, policy=policy,
                establisher=establisher, reviewer=reviewer, establish_mandate=establish_mandate,
                review_mandate=review_mandate,
                directory_writer=directory_writer, directory_mandate=directory_mandate,
                grant_mandate=grant_mandate, custody_mandate=custody_mandate, draft_source=source,
                source=accepted, entry=entry, data=data, tenant=tenant, args=args)
    install_binding(e, account=account)
    if account:
        e["args"]["student"] = "s1"
        e["args"]["students"] = [dict(student_id="s1", institution_id=tenant, register_number="0012",
            university_roll_number="roll-1" if roll else None, user_id="subject-user",
            auth_user_id="subject-auth", association_revision=1)]
    return e


class RevisedContractTests(unittest.TestCase):
    def setUp(self):
        self.e = fixture()
        self.o = self.e["o"]
        self.args = self.e["args"]

    def decide(self, **changes):
        return self.o.decide(**dict(self.args, **changes))

    def bind_profile(self):
        return install_binding(self.e, account=True)

    def manage(self, **changes):
        e = self.e
        args = dict(actor=e["grantor"], tenant=e["tenant"], mandate_id=e["grant_mandate"].mandate_id,
                    target=e["staff"], expected=1, request="revoke-1", grant=False,
                    reason="Synthetic revocation")
        return self.o.manage_permission(**dict(args, **changes))

    def accept(self, *, entry=None, source=None, **changes):
        e = self.e
        draft = source or replace(e["draft_source"], source_id="source-v2", version="fixture-v2",
                                  object_key="fixture-v2", object_version="object-v2")
        item = entry or replace(e["entry"], source_id=draft.source_id, entry_id="entry-v2")
        args = dict(actor=e["custodian"], tenant=e["tenant"], mandate_id=e["custody_mandate"].mandate_id,
                    policy_id=e["policy"].policy_id, source=draft, entries=[item],
                    original_bytes=b"synthetic second original copy", uploader=e["uploader"], now=30)
        accepted = self.o.accept_source(**dict(args, **changes))
        # This test helper separately obtains fresh proofing and review for the
        # new copy. Oracle.accept_source itself never creates account evidence.
        old = self.o.subject_bindings[(e["tenant"], "person-1")].evidence
        if item.raw_values.get("official_person_key") == "person-1":
            install_binding(e, account=old.mode == "account", source_id=accepted.source_id,
                entry_id=item.entry_id, profile_id=old.profile_id or "s1",
                user_id=old.user_id or "subject-user", auth_id=old.auth_id or "subject-auth",
                revision=old.association_revision or 1)
        return accepted

    def invalidate(self):
        e = self.e
        self.o.invalidate_source(actor=e["custodian"], tenant=e["tenant"],
            mandate_id=e["custody_mandate"].mandate_id, source_id=e["source"].source_id,
            reason="Synthetic integrity incident", evidence_reference="synthetic-incident-evidence")

    def student(self, **changes):
        return dict(dict(student_id="s1", institution_id=self.e["tenant"], register_number="0012",
                         university_roll_number="roll-1", user_id="subject-user", auth_user_id="subject-auth",
                         association_revision=1, approval_status="approved", status="active"), **changes)

    def finding(self, **changes):
        args = dict(actor=self.e["staff"], tenant=self.e["tenant"], request="finding-1",
                    source_id=self.e["source"].source_id, locator=self.e["entry"].locator,
                    finding="rejected_match", observed={"register_number": "9999"},
                    reason="Synthetic rejected candidate", entry_id=self.e["entry"].entry_id)
        return self.o.finding(**dict(args, **changes))

    def test_account_independent_positive_uses_full_retained_source(self):
        result = self.decide()
        head = self.o.identities[result["identity_id"]]["history"][-1]
        self.assertIsNone(head["student"])
        self.assertEqual(head["values"]["register_number"], "0012")
        self.assertEqual(head["evidence"]["raw_values"]["register_number"], " 0012 ")
        self.assertEqual(set(head["evidence"]["checked_identifiers"]), set(self.e["entry"].raw_values))
        self.assertEqual(head["evidence"]["source_manifest"]["sha256"], hashlib.sha256(self.e["data"]).hexdigest())

    def test_custody_server_hash_and_object_metadata(self):
        source = self.e["source"]
        self.assertEqual(source.sha256, hashlib.sha256(self.e["data"]).hexdigest())
        self.assertEqual(source.byte_length, len(self.e["data"]))
        self.assertEqual((source.version, source.as_of, source.object_version), ("fixture-v1", "2026-01-02", "object-version-1"))
        self.assertEqual(source.accepted_by, self.e["custodian"].user_id)
        self.assertEqual(source.entry_count, 1)

    def test_custody_refuses_client_digest_and_missing_object_version(self):
        for source in (replace(self.e["draft_source"], sha256="a"*64),
                       replace(self.e["draft_source"], object_version="")):
            with self.subTest(source=source), self.assertRaises(Refused):
                self.accept(source=replace(source, source_id="new-source"))

    def test_unapproved_or_wrong_tenant_source_is_not_usable(self):
        with self.assertRaises(Refused):
            self.decide(source_id="unaccepted-upload")
        with self.assertRaises(Refused):
            self.accept(source=replace(self.e["draft_source"], source_id="new-source", institution="other-tenant"))

    def test_custody_requires_current_designated_custodian(self):
        with self.assertRaises(Refused):
            self.accept(actor=self.e["staff"])
        self.o.mandate_revocations.add(self.e["custody_mandate"].mandate_id)
        with self.assertRaises(Refused):
            self.accept()

    def test_source_requires_valid_date_and_authenticity_reference(self):
        for change in (dict(as_of="2026-02-30"), dict(as_of="20260102"), dict(authenticity_reference=""),
                       dict(import_reference=""), dict(version=""), dict(bucket=""),
                       dict(authenticity_method=""), dict(provenance_description="")):
            with self.subTest(change=change), self.assertRaises(Refused):
                self.accept(source=replace(self.e["draft_source"], source_id="new-source", **change))

    def test_custody_refuses_ambiguous_entries_and_locators(self):
        source_id = "source-v2"
        first = replace(self.e["entry"], source_id=source_id, entry_id="v2a")
        second = replace(first, entry_id="v2b", locator="Sheet1!A3:C3")
        with self.assertRaisesRegex(Refused, "ambiguous_source"):
            self.accept(entries=[first, second])
        second = replace(second, locator=first.locator, raw_values={"official_person_key": "p2", "register_number": "0022"})
        with self.assertRaisesRegex(Refused, "locator_duplicate"):
            self.accept(entries=[first, second])

    def test_register_number_is_required_and_roll_is_optional(self):
        e = fixture(roll=False)
        e["o"].decide(**e["args"])
        for raw in ({"official_person_key": "p1", "university_roll_number": "r1"},
                    {"register_number": "0012"}, {"official_person_key": "p1", "register_number": 12}):
            with self.subTest(raw=raw), self.assertRaises(Refused):
                self.accept(entry=replace(self.e["entry"], entry_id="v2", source_id="source-v2", raw_values=raw))

    def test_no_client_official_values_parameter(self):
        with self.assertRaises(TypeError):
            self.decide(official_values={"register_number": "forged"})

    def test_entry_must_belong_to_selected_source(self):
        self.accept()
        with self.assertRaises(Refused):
            self.decide(entry_id="entry-v2")

    def test_corrupt_incomplete_source_is_refused_in_specification(self):
        self.o.sources[self.e["source"].source_id] = replace(self.e["source"], entry_count=2)
        with self.assertRaisesRegex(Refused, "source_incomplete"):
            self.decide()

    def test_missing_policy_or_governance_blocks_grant_and_positive(self):
        policy = self.e["policy"]
        invalid = [None, replace(policy, required=("official_person_key", "university_roll_number")),
                   replace(policy, required=("official_person_key", "register_number", "university_roll_number")),
                   replace(policy, rules={"register_number": "ascii_trim"}),
                   replace(policy, approvals={}), replace(policy, max_age_seconds=None)]
        for replacement in invalid:
            self.o.policies[self.e["tenant"]] = [] if replacement is None else [replacement]
            with self.subTest(policy=replacement), self.assertRaises(Refused):
                self.decide()
            with self.assertRaises(Refused):
                self.manage(target=replace(self.e["staff"], user_id="new-target"), expected=0,
                            request="new-grant", grant=True, policy_id=policy.policy_id)

    def test_normalization_policy_change_requires_collision_review(self):
        p = self.e["policy"]
        changed = replace(p, policy_id="new-policy", rules=dict(p.rules, register_number="exact"))
        self.o.policies[self.e["tenant"]].append(changed)
        with self.assertRaisesRegex(Refused, "collision_review"):
            self.decide(policy_id="new-policy")

    def test_exact_admin_individual_grant_is_supported(self):
        self.decide(actor=self.e["admin"])

    def test_role_and_wildcard_permissions_do_not_substitute(self):
        for permissions in (frozenset(), frozenset({"*"}), frozenset({"academic_identity.verify"})):
            stranger = replace(self.e["staff"], user_id="unassigned", permissions=permissions)
            with self.subTest(permissions=permissions), self.assertRaisesRegex(Refused, "explicit_individual_permission"):
                self.decide(actor=stranger)

    def test_inactive_ambiguous_or_wrong_scope_actor_is_denied(self):
        actor = self.e["staff"]
        invalid = [replace(actor, active=False), replace(actor, auth_linked=False),
                   replace(actor, institution_active=False), replace(actor, role_active=False),
                   replace(actor, parent_matches=False), replace(actor, service_caller=False),
                   replace(actor, role="faculty"), replace(actor, role="student"),
                   replace(actor, scopes=()), replace(actor, scopes=("other",)),
                   replace(actor, scopes=(self.e["tenant"], "other"))]
        for candidate in invalid:
            with self.subTest(actor=candidate), self.assertRaises(Refused):
                self.decide(actor=candidate)

    def test_self_grant_and_self_revoke_are_denied(self):
        for grant in (True, False):
            with self.subTest(grant=grant), self.assertRaisesRegex(Refused, "self_assignment"):
                self.manage(target=self.e["grantor"], grant=grant, expected=0)

    def test_grantor_must_have_active_admin_membership_and_mandate(self):
        for change in (dict(actor=self.e["staff"]), dict(mandate_id="missing"),
                       dict(actor=replace(self.e["grantor"], active=False))):
            with self.subTest(change=change), self.assertRaises(Refused):
                self.manage(**change)

    def test_revocation_reauthorizes_retry_and_preserves_prior_event(self):
        self.decide()
        self.manage()
        self.assertEqual([x["state"] for x in self.o.permission_events[(self.e["tenant"], self.e["staff"].user_id)]], ["granted", "revoked"])
        with self.assertRaises(Refused):
            self.decide()
        # Grantor remains authorized: management retry adds no duplicate audit.
        count = len(self.o.audit_events)
        self.assertTrue(self.manage()["replayed"])
        self.assertEqual(len(self.o.audit_events), count)

    def test_revocation_works_without_policy_and_for_inactive_target(self):
        self.o.policies[self.e["tenant"]] = []
        self.manage(target=replace(self.e["staff"], active=False))
        self.assertEqual(self.o.permission_events[(self.e["tenant"], self.e["staff"].user_id)][-1]["state"], "revoked")

    def test_target_permission_stale_revision_conflicts(self):
        with self.assertRaisesRegex(Refused, "permission_revision"):
            self.manage(expected=0)

    def test_mandate_revocation_blocks_management_but_not_prior_assignments(self):
        self.o.mandate_revocations.add(self.e["grant_mandate"].mandate_id)
        with self.assertRaises(Refused):
            self.manage()
        self.decide()

    def test_cross_tenant_permission_cannot_authorize(self):
        e2 = fixture(tenant="institution-b", oracle=self.o)
        with self.assertRaises(Refused):
            self.decide(actor=e2["staff"])

    def test_disabled_capability_denies_even_historical_retry(self):
        self.decide()
        self.o.capability_active = False
        with self.assertRaises(Refused):
            self.decide()

    def test_management_old_grant_retry_does_not_restore_revoked_permission(self):
        self.manage()
        replay = self.manage(expected=0, request="setup-grant-0", grant=True,
            reason="Synthetic explicit assignment", policy_id=self.e["policy"].policy_id)
        self.assertEqual((replay["recorded_revision"], replay["head_revision"]), (1, 2))
        self.assertEqual(self.o.permission_events[(self.e["tenant"], self.e["staff"].user_id)][-1]["state"], "revoked")

    def test_unique_ownership_institution_wide_but_tenants_independent(self):
        self.decide()
        with self.assertRaisesRegex(Refused, "identity_conflict"):
            self.decide(identity="second-identity", request="verify-2")
        e2 = fixture(tenant="institution-b", oracle=self.o)
        e2["o"].decide(**e2["args"])

    def test_trim_variant_conflicts_and_leading_zeros_are_distinct(self):
        self.decide()
        source = self.accept(entry=replace(self.e["entry"], entry_id="entry-v2", source_id="source-v2",
            raw_values={"official_person_key": "person-2", "register_number": "0012", "university_roll_number": "roll-2"}))
        with self.assertRaisesRegex(Refused, "identity_conflict"):
            self.decide(identity="other", request="v2", source_id=source.source_id, entry_id="entry-v2")
        self.assertNotEqual(normalize("0012", "ascii_trim"), normalize("12", "ascii_trim"))

    def test_every_source_roll_is_checked_against_actual_profile(self):
        self.bind_profile()
        with self.assertRaisesRegex(Refused, "identity_conflict"):
            self.decide(student="s1", students=[self.student(university_roll_number="other-roll")])

    def test_missing_source_roll_does_not_hide_candidate_roll(self):
        e = fixture(roll=False, account=True)
        row = self.student()
        with self.assertRaises(Refused):
            e["o"].decide(**dict(e["args"], student="s1", students=[row]))

    def test_roll_only_or_student_number_only_never_links_profile(self):
        self.bind_profile()
        for row in (self.student(register_number=None), self.student(register_number=None, university_roll_number=None, student_number="0012")):
            with self.subTest(row=row), self.assertRaises(Refused):
                self.decide(student="s1", students=[row])

    def test_no_first_candidate_selection(self):
        self.bind_profile()
        rows = [self.student(), self.student(student_id="s2")]
        for ordered in (rows, list(reversed(rows))):
            with self.assertRaisesRegex(Refused, "link_conflict"):
                self.decide(student="s1", students=ordered)

    def test_two_identifiers_pointing_to_different_profiles_conflict(self):
        self.bind_profile()
        rows = [self.student(university_roll_number=None), self.student(student_id="s2", register_number="other")]
        with self.assertRaises(Refused):
            self.decide(student="s1", students=rows)

    def test_explicit_link_required_and_legacy_rows_are_unchanged(self):
        self.bind_profile()
        rows = [self.student()]
        rosters = [dict(institution_id=self.e["tenant"], roster_id=f"r{i}", section_id=f"section-{i}",
                        register_number="0012", university_roll_number="roll-1", linked_student_id="s1") for i in (1, 2)]
        before = deepcopy((rows, rosters))
        with self.assertRaises(Refused):
            self.decide(students=rows, rosters=rosters)
        self.decide(student="s1", students=rows, rosters=rosters)
        self.assertEqual((rows, rosters), before)
        head = self.o.identities[self.args["identity"]]["history"][-1]
        self.assertEqual(len(head["evidence"]["observed_rosters"]), 2)

    def test_conflicting_roster_roll_or_link_blocks_positive(self):
        for change in (dict(university_roll_number="other"), dict(linked_student_id="other-student")):
            roster = dict(institution_id=self.e["tenant"], register_number="0012", university_roll_number="roll-1")
            roster.update(change)
            with self.subTest(roster=roster), self.assertRaises(Refused):
                self.decide(rosters=[roster])

    def test_approved_active_or_linked_legacy_state_is_not_verification(self):
        self.assertFalse(self.o.current_usable(self.e["tenant"], self.args["identity"], self.e["policy"].policy_id, now=1000))
        self.assertEqual(self.o.identities, {})

    def test_candidate_rejection_never_changes_existing_positive_ownership(self):
        self.decide()
        before = deepcopy((self.o.identities, self.o.claims, self.o.historical_owners))
        self.finding(context=self.args["identity"])
        self.assertEqual((self.o.identities, self.o.claims, self.o.historical_owners), before)

    def test_unresolved_and_no_match_findings_create_no_identity_or_claim(self):
        self.finding(finding="unresolved", entry_id=None, locator="Sheet1 rows 2-200")
        self.assertEqual(self.o.identities, {})
        self.assertEqual(self.o.claims, {})

    def test_finding_exact_locator_and_context_are_scoped(self):
        for change in (dict(locator="wrong-row"), dict(context="missing-identity"),
                       dict(candidate="missing-profile"), dict(source_id="unaccepted")):
            with self.subTest(change=change), self.assertRaises(Refused):
                self.finding(**change)

    def test_candidate_retry_has_one_finding_and_audit(self):
        count = len(self.o.audit_events)
        self.finding()
        self.assertTrue(self.finding()["replayed"])
        self.assertEqual(len(self.o.findings), 1)
        self.assertEqual(len(self.o.audit_events), count+1)
        record = self.o.findings[0]
        self.assertEqual((record["verifier"], record["auth"], record["institution"], record["recorded_at"]),
                         (self.e["staff"].user_id, self.e["staff"].auth_id, self.e["tenant"], 1000))
        self.assertEqual(record["verifier_permission_event"]["permission_code"], "academic_identity.verify")

    def test_candidate_retry_after_permission_revocation_is_denied(self):
        self.finding()
        self.manage()
        with self.assertRaises(Refused):
            self.finding()

    def test_same_key_retries_once_changed_payload_conflicts(self):
        count = len(self.o.audit_events)
        self.decide()
        self.assertTrue(self.decide()["replayed"])
        self.assertEqual(len(self.o.audit_events), count+1)
        with self.assertRaisesRegex(Refused, "idempotency_conflict"):
            self.decide(reason="Different request")

    def test_stale_revision_is_not_rebased(self):
        self.decide()
        with self.assertRaisesRegex(Refused, "revision_or_resource"):
            self.decide(request="new-key")

    def test_independent_reverification_appends_revision(self):
        self.decide()
        self.decide(operation="reverify", expected=1, request="recheck")
        history = self.o.identities[self.args["identity"]]["history"]
        self.assertEqual([h["revision"] for h in history], [1, 2])
        self.assertEqual(history[1]["supersedes"], 1)

    def test_changed_values_require_correction_and_preserve_raw_history(self):
        self.decide()
        entry = replace(self.e["entry"], entry_id="entry-v2", source_id="source-v2",
                        raw_values=dict(self.e["entry"].raw_values, register_number="0099"))
        self.accept(entry=entry)
        with self.assertRaisesRegex(Refused, "correction_required"):
            self.decide(operation="reverify", expected=1, request="recheck", source_id="source-v2", entry_id="entry-v2")
        self.decide(operation="correct", expected=1, request="correct", source_id="source-v2", entry_id="entry-v2")
        history = self.o.identities[self.args["identity"]]["history"]
        self.assertEqual(history[0]["evidence"]["raw_values"]["register_number"], " 0012 ")
        self.assertEqual(history[1]["values"]["register_number"], "0099")
        self.assertIn((self.e["tenant"], "register_number", "0012"), self.o.historical_owners)

    def test_wrong_person_key_is_never_ordinary_correction(self):
        self.decide()
        entry = replace(self.e["entry"], entry_id="entry-v2", source_id="source-v2",
                        raw_values=dict(self.e["entry"].raw_values, official_person_key="another-person"))
        self.accept(entry=entry)
        with self.assertRaisesRegex(Refused, "reassociation"):
            self.decide(operation="correct", expected=1, request="wrong-person", source_id="source-v2", entry_id="entry-v2")

    def test_withdrawal_works_after_invalidation_and_missing_policy(self):
        self.decide()
        self.invalidate()
        self.o.policies[self.e["tenant"]] = []
        self.decide(operation="withdraw", expected=1, request="withdraw", policy_id=None, source_id=None, entry_id=None)
        self.assertEqual(self.o.claims, {})
        self.assertTrue(self.o.historical_owners)
        self.assertIn(self.e["source"].source_id, self.o.sources)
        old_retry = self.decide()
        self.assertEqual((old_retry["recorded_decision"], old_retry["head_revision"]), ("verified", 2))

    def test_withdrawal_does_not_allow_new_register_assertions(self):
        self.decide()
        with self.assertRaisesRegex(Refused, "withdrawal_input"):
            self.decide(operation="withdraw", expected=1, request="withdraw")

    def test_withdrawal_preserves_link_and_repeated_withdrawal_is_refused(self):
        self.bind_profile()
        rows = [self.student()]
        self.decide(student="s1", students=rows)
        before = deepcopy(rows)
        self.decide(operation="withdraw", expected=1, request="withdraw", policy_id=None, source_id=None, entry_id=None)
        self.assertEqual(self.o.identities[self.args["identity"]]["student"], "s1")
        self.assertEqual(rows, before)
        with self.assertRaises(Refused):
            self.decide(operation="withdraw", expected=2, request="withdraw-again", policy_id=None, source_id=None, entry_id=None)

    def test_withdrawal_never_transfers_historical_ownership(self):
        self.decide()
        self.decide(operation="withdraw", expected=1, request="withdraw", policy_id=None, source_id=None, entry_id=None)
        with self.assertRaisesRegex(Refused, "identity_conflict"):
            self.decide(identity="different-person", request="transfer")

    def test_withdrawn_identity_restores_only_through_explicit_correction(self):
        self.decide()
        self.decide(operation="withdraw", expected=1, request="withdraw",
                    policy_id=None, source_id=None, entry_id=None)
        self.accept()
        with self.assertRaises(Refused):
            self.decide(operation="reverify", expected=2, request="restore-as-reverify",
                        source_id="source-v2", entry_id="entry-v2")
        self.decide(operation="correct", expected=2, request="restore-as-correction",
                    source_id="source-v2", entry_id="entry-v2")
        self.assertEqual(self.o.identities[self.args["identity"]]["head"], 3)

    def test_non_null_profile_link_cannot_be_reassigned(self):
        self.bind_profile()
        self.decide(student="s1", students=[self.student()])
        with self.assertRaisesRegex(Refused, "reassociation"):
            self.decide(operation="correct", expected=1, request="move-profile",
                        student="s2", students=[self.student(student_id="s2")])

    def test_source_invalidation_blocks_use_without_erasing_history_or_claims(self):
        self.decide()
        before = deepcopy((self.o.identities, self.o.claims))
        self.invalidate()
        self.assertFalse(self.o.current_usable(self.e["tenant"], self.args["identity"], self.e["policy"].policy_id, now=1001))
        self.assertEqual((self.o.identities, self.o.claims), before)
        with self.assertRaises(Refused):
            self.decide(operation="reverify", expected=1, request="new-check")

    def test_source_invalidation_needs_custodian_but_no_new_policy(self):
        self.o.policies[self.e["tenant"]] = []
        with self.assertRaises(Refused):
            self.o.invalidate_source(actor=self.e["staff"], tenant=self.e["tenant"],
                mandate_id=self.e["custody_mandate"].mandate_id, source_id=self.e["source"].source_id,
                reason="Incident", evidence_reference="synthetic-incident-evidence")
        self.invalidate()

    def test_old_retry_after_source_invalidation_is_historical_only(self):
        self.decide()
        self.invalidate()
        self.assertTrue(self.decide()["replayed"])
        self.assertFalse(self.o.current_usable(self.e["tenant"], self.args["identity"], self.e["policy"].policy_id, now=1001))

    def test_expiry_boundary_and_later_legacy_conflict_are_projection_rules_only(self):
        self.decide(now=1000)
        current = lambda now, **kw: self.o.current_usable(self.e["tenant"], self.args["identity"], self.e["policy"].policy_id, now=now, **kw)
        self.assertTrue(current(4599))
        self.assertFalse(current(4600))
        self.assertFalse(current(1001, students=[self.student(university_roll_number="conflict")]))
        self.assertTrue(self.o.claims)  # Expiry never silently releases ownership.

    def test_explicit_no_expiry_differs_from_missing_policy(self):
        p = replace(self.e["policy"], freshness_mode="no_expiry", max_age_seconds=None)
        self.o.policies[self.e["tenant"]] = [p]
        self.decide()
        self.assertTrue(self.o.current_usable(self.e["tenant"], self.args["identity"], p.policy_id, now=10**9))
        self.o.policies[self.e["tenant"]] = []
        self.assertFalse(self.o.current_usable(self.e["tenant"], self.args["identity"], p.policy_id, now=1001))

    def test_missing_optional_issuer_metadata_is_recorded_without_invention(self):
        draft = replace(self.e["draft_source"], source_id="source-v2", version=None,
                        as_of=None, issuer=None, object_key="copy-v2", object_version="v2",
                        missing_metadata_reason="Custodian confirmed copy has no issuer label, version or date")
        accepted = self.accept(source=draft)
        self.assertIsNone(accepted.version)
        self.assertIsNone(accepted.as_of)
        self.assertIsNone(accepted.issuer)
        self.decide(source_id=accepted.source_id, entry_id="entry-v2")
        self.assertEqual(self.o.identities[self.args["identity"]]["history"][-1]
                         ["evidence"]["source_manifest"]["missing_metadata_reason"], draft.missing_metadata_reason)

    def test_unexplained_missing_metadata_is_refused(self):
        for change in (dict(version=None), dict(as_of=None), dict(issuer=None)):
            with self.subTest(change=change), self.assertRaises(Refused):
                self.accept(source=replace(self.e["draft_source"], source_id="source-v2", **change))

    def test_filename_reference_and_digest_do_not_replace_authenticity_evidence(self):
        for change in (dict(authenticity_reference=""), dict(authenticity_method=""),
                       dict(provenance_description="")):
            with self.subTest(change=change), self.assertRaises(Refused):
                self.accept(source=replace(self.e["draft_source"], source_id="source-v2", **change))

    def test_upload_requires_explicit_institution_authority_and_actor_pair(self):
        for change in (dict(uploader=self.e["admin"]),
                       dict(uploader=replace(self.e["uploader"], scopes=("other",))),
                       dict(uploader=replace(self.e["uploader"], auth_id="forged"))):
            with self.subTest(change=change), self.assertRaises(Refused):
                self.accept(**change)
        self.o.mandate_revocations.add(self.e["upload_mandate"].mandate_id)
        with self.assertRaises(Refused):
            self.accept()

    def test_permission_event_retains_provenance_scope_time_and_reason(self):
        self.manage(now=1100)
        events = self.o.permission_events[(self.e["tenant"], self.e["staff"].user_id)]
        self.assertEqual([e["recorded_at"] for e in events], [1000, 1100])
        for event in events:
            self.assertEqual(event["permission_code"], "academic_identity.verify")
            self.assertEqual(event["institution"], self.e["tenant"])
            self.assertEqual(event["target"], self.e["staff"].user_id)
            self.assertEqual(event["actor"], self.e["grantor"].user_id)
            self.assertTrue(event["reason"])

    def test_incomplete_or_wildcard_event_provenance_never_authorizes(self):
        key = (self.e["tenant"], self.e["staff"].user_id)
        original = deepcopy(self.o.permission_events[key])
        for change in (dict(permission_code="*"), dict(permission_code="academic_identity.*"),
                       dict(institution="other"), dict(target="someone-else"),
                       dict(mandate="missing"), dict(auth=""), dict(recorded_at=None)):
            self.o.permission_events[key] = [dict(original[-1], **change)]
            with self.subTest(change=change), self.assertRaisesRegex(Refused, "permission_provenance"):
                self.decide()
        self.o.permission_events[key] = original

    def test_admin_status_alone_cannot_verify(self):
        with self.assertRaisesRegex(Refused, "explicit_individual_permission"):
            self.decide(actor=replace(self.e["admin"], user_id="unassigned-admin",
                                      permissions=frozenset({"*", "academic_identity.verify"})))

    def test_self_approval_checks_user_and_auth_for_all_positive_operations(self):
        for operation in ("verify", "reverify", "correct"):
            for identifier in ("user_id", "auth_id"):
                e = fixture(account=True)
                o = e["o"]
                if operation != "verify":
                    o.decide(**e["args"])
                changed = {identifier: e["staff"].user_id if identifier == "user_id" else e["staff"].auth_id}
                install_binding(e, account=True, **changed)
                before = deepcopy((o.identities, o.claims, o.audit_events))
                with self.subTest(operation=operation, identifier=identifier), self.assertRaisesRegex(Refused, "self_approval"):
                    o.decide(**dict(e["args"], operation=operation,
                                    expected=0 if operation == "verify" else 1, request="self-approval"))
                self.assertEqual((o.identities, o.claims, o.audit_events), before)

    def test_linked_student_user_cannot_be_own_verifier(self):
        self.bind_profile()
        for row in (self.student(user_id=self.e["staff"].user_id),
                    self.student(auth_user_id=self.e["staff"].auth_id)):
            with self.subTest(row=row), self.assertRaisesRegex(Refused, "self_approval"):
                self.decide(student="s1", students=[row])

    def test_subject_binding_requires_independent_review_and_evidence(self):
        key = (self.e["tenant"], "person-1")
        binding = self.o.subject_bindings[key]
        for replacement in (None, replace(binding, evidence=replace(binding.evidence, institution="other")),
                            replace(binding, evidence=replace(binding.evidence, provenance_reference="")),
                            replace(binding, reviewer_user_id=self.e["staff"].user_id),
                            replace(binding, evidence=replace(binding.evidence, user_id=binding.reviewer_user_id))):
            self.o.subject_bindings[key] = replacement
            with self.subTest(binding=replacement), self.assertRaises(Refused):
                self.decide()

    def test_missing_freshness_is_unresolved_without_new_history(self):
        p = self.e["policy"]
        for mode, age in (("undecided", None), ("bounded", None)):
            self.o.policies[self.e["tenant"]] = [replace(p, freshness_mode=mode, max_age_seconds=age)]
            with self.subTest(mode=mode), self.assertRaises(UnresolvedPolicy):
                self.decide()
        self.assertEqual(self.o.identities, {})

    def test_historical_identifier_reuse_reports_unresolved_owner_policy(self):
        self.decide()
        self.decide(operation="withdraw", expected=1, request="withdraw",
                    policy_id=None, source_id=None, entry_id=None)
        with self.assertRaisesRegex(UnresolvedPolicy, "identifier_reuse_unresolved"):
            self.decide(identity="new-person", request="reuse")

    def test_blank_missing_and_roll_substituted_register_fail_closed(self):
        for raw in ({"official_person_key": "p1", "register_number": ""},
                    {"official_person_key": "p1", "register_number": " \t"},
                    {"official_person_key": "p1", "university_roll_number": "0012"},
                    {"official_person_key": "p1", "student_number": "0012"}):
            with self.subTest(raw=raw), self.assertRaises(Refused):
                self.accept(entry=replace(self.e["entry"], entry_id="entry-v2", source_id="source-v2", raw_values=raw))

    def test_ambiguous_spreadsheet_or_ocr_strings_are_not_silently_accepted(self):
        for status in ("unreviewed", "numeric_coercion", "ocr_ambiguous", "formula_unresolved"):
            with self.subTest(status=status), self.assertRaisesRegex(Refused, "ambiguous_extraction"):
                self.accept(entry=replace(self.e["entry"], entry_id="entry-v2", source_id="source-v2",
                                          extraction_status=status))

    def test_missing_normalization_approval_reports_unresolved_policy(self):
        p = self.e["policy"]
        approvals = dict(p.approvals)
        del approvals["normalization"]
        self.o.policies[self.e["tenant"]] = [replace(p, approvals=approvals)]
        with self.assertRaises(UnresolvedPolicy):
            self.decide()

    def test_replacement_preserves_old_source_and_decision_without_automatic_transition(self):
        self.decide()
        before = deepcopy((self.o.identities, self.o.claims, self.e["source"]))
        self.accept()
        self.assertEqual((self.o.identities, self.o.claims, self.o.sources[self.e["source"].source_id]), before)
        self.assertEqual(len(self.o.sources), 2)

    def test_rejection_operation_cannot_be_used_as_withdrawal(self):
        self.decide()
        before = deepcopy((self.o.identities, self.o.claims, self.o.audit_events))
        with self.assertRaises(Refused):
            self.decide(operation="rejected_match", expected=1, request="wrong-command")
        self.assertEqual((self.o.identities, self.o.claims, self.o.audit_events), before)

    def test_unverified_candidate_cannot_be_withdrawn(self):
        self.finding()
        with self.assertRaises(Refused):
            self.decide(operation="withdraw", policy_id=None, source_id=None, entry_id=None)
        self.assertEqual(self.o.identities, {})

    def test_revoked_verifier_cannot_withdraw_after_source_invalidation(self):
        self.decide()
        self.invalidate()
        self.manage()
        with self.assertRaisesRegex(Refused, "explicit_individual_permission"):
            self.decide(operation="withdraw", expected=1, request="withdraw",
                        policy_id=None, source_id=None, entry_id=None)

    def test_withdrawal_is_not_a_new_positive_self_approval(self):
        self.decide()
        install_binding(self.e, account=True, user_id=self.e["staff"].user_id)
        self.decide(operation="withdraw", expected=1, request="withdraw",
                    policy_id=None, source_id=None, entry_id=None)
        self.assertEqual(self.o.identities[self.args["identity"]]["history"][-1]["decision"], "withdrawn")

    def test_invalidation_retains_incident_provenance_and_original_positive(self):
        self.decide()
        original = deepcopy(self.o.identities[self.args["identity"]]["history"])
        self.invalidate()
        incident = self.o.invalidations[self.e["source"].source_id]
        self.assertEqual(incident["actor"], self.e["custodian"].user_id)
        self.assertEqual(incident["evidence_reference"], "synthetic-incident-evidence")
        self.assertEqual(incident["recorded_at"], 1000)
        self.assertEqual(self.o.identities[self.args["identity"]]["history"], original)


class SubjectBindingAdversarialTests(unittest.TestCase):
    operations = ("verify", "reverify", "correct")

    def prepare(self, operation, *, expiry=None):
        e = fixture(account=True)
        if expiry is not None:
            install_binding(e, account=True, valid_until=expiry)
        if operation != "verify":
            e["o"].decide(**dict(e["args"], now=900))
        args = dict(e["args"], operation=operation, expected=0 if operation == "verify" else 1,
                    request="adversarial-command", now=1000)
        return e, args

    def assert_refused_unchanged(self, e, args, *, usable=False, code=None):
        o = e["o"]
        before = deepcopy((o.identities, o.claims, o.historical_owners, o.receipts, o.audit_events, args["students"]))
        denied = len(o.denials)
        with self.assertRaises(Refused) as refused:
            o.decide(**args)
        if code is not None:
            self.assertEqual(str(refused.exception), code)
        self.assertEqual((o.identities, o.claims, o.historical_owners, o.receipts, o.audit_events, args["students"]), before)
        self.assertEqual(len(o.denials), denied + 1)
        self.assertEqual(o.denials[-1]["operation"], args["operation"])
        self.assertEqual(o.current_usable(e["tenant"], args["identity"], e["policy"].policy_id,
            now=args["now"], students=args["students"]), usable)

    def test_review_probe_no_accounts_cannot_authorize_selected_account(self):
        for operation in self.operations:
            for directory_present in (True, False):
                with self.subTest(operation=operation, directory_present=directory_present):
                    e, args = self.prepare(operation)
                    if not directory_present:
                        e["o"].record_directory_change(actor=e["directory_writer"], tenant=e["tenant"],
                            mandate_id=e["directory_mandate"].mandate_id,
                            expected_generation=e["o"].directory_heads[e["tenant"]].generation,
                            associations=(), operation="remove", reason="Synthetic probe removes association", now=30)
                    install_binding(e, account=False)
                    self.assert_refused_unchanged(e, args, code="binding_no_accounts")

    def test_review_probe_account_b_cannot_authorize_profile_account_a(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                install_binding(e, account=True, user_id="account-b", auth_id="auth-b")
                self.assert_refused_unchanged(e, args)

    def test_register_match_cannot_replace_missing_account_ownership(self):
        for operation in self.operations:
            for field in ("user_id", "auth_user_id", "association_revision"):
                with self.subTest(operation=operation, missing=field):
                    e, args = self.prepare(operation)
                    args["students"] = [dict(args["students"][0], **{field: None})]
                    self.assert_refused_unchanged(e, args)

    def test_missing_trusted_account_directory_cannot_be_replaced_by_profile_identifiers(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                e["o"].account_associations.clear()
                self.assert_refused_unchanged(e, args)

    def test_roll_match_without_register_refuses_all_positives(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                args["students"] = [dict(args["students"][0], register_number=None)]
                self.assert_refused_unchanged(e, args)

    def test_foreign_binding_cannot_be_used_in_current_institution(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                foreign = fixture(tenant="other")
                e["o"].subject_bindings[(e["tenant"], "person-1")] = foreign["o"].subject_bindings[("other", "person-1")]
                self.assert_refused_unchanged(e, args)

    def test_stale_binding_boundary_refuses_all_positives(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation, expiry=1000)
                self.assert_refused_unchanged(e, args)

    def test_revoked_binding_or_evidence_refuses_all_positives(self):
        for operation in self.operations:
            for kind in ("binding", "evidence"):
                with self.subTest(operation=operation, revoked=kind):
                    e, args = self.prepare(operation)
                    o = e["o"]
                    binding = o.subject_bindings[(e["tenant"], "person-1")]
                    if kind == "binding":
                        o.binding_revocations.add(binding.binding_id)
                    else:
                        o.evidence_revocations.add(binding.evidence.evidence_id)
                    self.assert_refused_unchanged(e, args)

    def test_incomplete_contradictory_or_unregistered_receipt_refuses_all_positives(self):
        for operation in self.operations:
            for change in (dict(complete=False), dict(auth_id=None), dict(mode="no_accounts"),
                           dict(person_key="other-subject"), dict(entry_id="other-entry"),
                           dict(source_id="other-version"), dict(provenance_reference="")):
                with self.subTest(operation=operation, change=change):
                    e, args = self.prepare(operation)
                    o = e["o"]
                    key = (e["tenant"], "person-1")
                    binding = o.subject_bindings[key]
                    o.subject_bindings[key] = replace(binding, evidence=replace(binding.evidence, **change))
                    self.assert_refused_unchanged(e, args)

    def test_authoritative_association_change_after_collection_refuses_all_positives(self):
        changes = (dict(user_id="account-b"), dict(auth_id="auth-b"), dict(profile_id="profile-b"),
                   dict(person_key="other-subject"), dict(institution="other"), dict(revision=2), dict(active=False))
        for operation in self.operations:
            for change in changes:
                with self.subTest(operation=operation, change=change):
                    e, args = self.prepare(operation)
                    key = (e["tenant"], "s1")
                    e["o"].account_associations[key] = replace(e["o"].account_associations[key], **change)
                    self.assert_refused_unchanged(e, args)

    def test_account_or_auth_shared_with_another_subject_refuses_all_positives(self):
        for operation in self.operations:
            for same in ("user", "auth"):
                with self.subTest(operation=operation, shared=same):
                    e, args = self.prepare(operation)
                    e["o"].account_associations[(e["tenant"], "other-profile")] = AccountAssociation(
                        e["tenant"], "other-person", "other-profile",
                        "subject-user" if same == "user" else "other-user",
                        "subject-auth" if same == "auth" else "other-auth", 1)
                    self.assert_refused_unchanged(e, args)

    def test_profile_account_auth_or_profile_id_change_invalidates_existing_head(self):
        for change in (dict(user_id="new-user"), dict(auth_user_id="new-auth"),
                       dict(student_id="new-profile"), dict(institution_id="other"), dict(association_revision=2)):
            e = fixture(account=True)
            o = e["o"]
            o.decide(**e["args"])
            original = deepcopy(o.identities)
            rows = [dict(e["args"]["students"][0], **change)]
            with self.subTest(change=change):
                self.assertFalse(o.current_usable(e["tenant"], e["args"]["identity"], e["policy"].policy_id,
                                                 now=1001, students=rows))
                self.assertEqual(o.identities, original)

    def test_matching_new_account_and_new_evidence_cannot_transfer_existing_verification(self):
        for operation in ("reverify", "correct"):
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                install_binding(e, account=True, user_id="account-b", auth_id="auth-b", revision=2)
                args["students"] = [dict(args["students"][0], user_id="account-b", auth_user_id="auth-b", association_revision=2)]
                self.assert_refused_unchanged(e, args)

    def test_previously_unlinked_positive_cannot_gain_account_by_ordinary_correction(self):
        e = fixture()
        e["o"].decide(**e["args"])
        install_binding(e, account=True)
        rows = [dict(student_id="s1", institution_id=e["tenant"], register_number="0012",
                     university_roll_number="roll-1", user_id="subject-user", auth_user_id="subject-auth", association_revision=1)]
        self.assert_refused_unchanged(e, dict(e["args"], student="s1", students=rows,
            operation="correct", expected=1, request="attach-account", now=1001))

    def test_binding_approval_requires_exact_authorized_reviewer_and_provenance(self):
        for change in ("unmandated_admin", "forged_auth", "wrong_mandate", "revoked_mandate", "wrong_scope"):
            with self.subTest(change=change):
                e = fixture(account=True)
                o = e["o"]
                binding = o.subject_bindings[(e["tenant"], "person-1")]
                actor, mandate = e["reviewer"], e["review_mandate"].mandate_id
                if change == "unmandated_admin":
                    actor = e["admin"]
                elif change == "forged_auth":
                    actor = replace(actor, auth_id="forged")
                elif change == "wrong_mandate":
                    mandate = e["grant_mandate"].mandate_id
                elif change == "revoked_mandate":
                    o.mandate_revocations.add(mandate)
                else:
                    actor = replace(actor, scopes=("other",))
                before = deepcopy((o.subject_bindings, o.binding_history, o.audit_events))
                denied = len(o.denials)
                with self.assertRaises(Refused):
                    o.approve_binding(actor=actor, tenant=e["tenant"], mandate_id=mandate,
                        binding_id="unauthorized", evidence_id=binding.evidence.evidence_id,
                        policy_id=e["policy"].policy_id, now=60)
                self.assertEqual((o.subject_bindings, o.binding_history, o.audit_events), before)
                self.assertNotIn("unauthorized", o.binding_history)
                self.assertEqual(len(o.denials), denied + 1)
                self.assertEqual(o.denials[-1]["operation"], "approve_binding")

    def test_registered_malformed_receipt_cannot_obtain_approval(self):
        changes = (dict(complete=False), dict(auth_id=None), dict(mode="no_accounts"),
                   dict(collected_at=51), dict(valid_until=50), dict(valid_until=None),
                   dict(provenance_reference=""), dict(method="unapproved"),
                   dict(person_key="other-person"), dict(establisher_mandate_id="missing"))
        for change in changes:
            with self.subTest(change=change):
                e = fixture(account=True)
                o = e["o"]
                binding = o.subject_bindings[(e["tenant"], "person-1")]
                receipt = replace(binding.evidence, evidence_id="malformed-proof", **change)
                o.binding_evidence[receipt.evidence_id] = receipt
                before = deepcopy((o.subject_bindings, o.binding_history, o.audit_events, o.identities, o.claims))
                with self.assertRaises(Refused):
                    o.approve_binding(actor=e["reviewer"], tenant=e["tenant"],
                        mandate_id=e["review_mandate"].mandate_id, binding_id="malformed-approval",
                        evidence_id=receipt.evidence_id, policy_id=e["policy"].policy_id, now=50)
                self.assertEqual((o.subject_bindings, o.binding_history, o.audit_events, o.identities, o.claims), before)
                self.assertNotIn("malformed-approval", o.binding_history)
                self.assertFalse(o.current_usable(e["tenant"], e["args"]["identity"], e["policy"].policy_id,
                                                 now=1001, students=e["args"]["students"]))

    def test_reviewer_or_establisher_revocation_blocks_new_positives_and_usability(self):
        for operation in self.operations:
            for authority in ("review_mandate", "establish_mandate"):
                with self.subTest(operation=operation, authority=authority):
                    e, args = self.prepare(operation)
                    e["o"].mandate_revocations.add(e[authority].mandate_id)
                    self.assert_refused_unchanged(e, args)

    def test_self_approval_refuses_all_positives_without_changing_state(self):
        for operation in self.operations:
            for identifier in ("user_id", "auth_id"):
                with self.subTest(operation=operation, identifier=identifier):
                    e, args = self.prepare(operation)
                    install_binding(e, account=True, **{
                        identifier: e["staff"].user_id if identifier == "user_id" else e["staff"].auth_id})
                    self.assert_refused_unchanged(e, args)

    def test_subject_cannot_approve_own_binding_receipt(self):
        e = fixture(account=True)
        o = e["o"]
        original = o.subject_bindings[(e["tenant"], "person-1")]
        receipt = replace(original.evidence, evidence_id="self-review-proof",
                          user_id=e["reviewer"].user_id, auth_id=e["reviewer"].auth_id)
        o.binding_evidence[receipt.evidence_id] = receipt
        before = deepcopy((o.subject_bindings, o.binding_history, o.audit_events, o.identities, o.claims))
        with self.assertRaises(Refused):
            o.approve_binding(actor=e["reviewer"], tenant=e["tenant"],
                mandate_id=e["review_mandate"].mandate_id, binding_id="self-approved",
                evidence_id=receipt.evidence_id, policy_id=e["policy"].policy_id, now=60)
        self.assertEqual((o.subject_bindings, o.binding_history, o.audit_events, o.identities, o.claims), before)
        self.assertFalse(o.current_usable(e["tenant"], e["args"]["identity"], e["policy"].policy_id,
                                         now=1001, students=e["args"]["students"]))

    def test_unlinked_subject_becomes_unusable_when_authoritative_account_appears(self):
        e = fixture()
        o = e["o"]
        o.decide(**e["args"])
        original = deepcopy(o.identities)
        o.account_associations[(e["tenant"], "s1")] = AccountAssociation(
            e["tenant"], "person-1", "s1", "new-user", "new-auth", 1)
        self.assertFalse(o.current_usable(e["tenant"], e["args"]["identity"], e["policy"].policy_id, now=1001))
        self.assertEqual(o.identities, original)

    def test_historical_positive_without_binding_snapshot_cannot_be_upgraded(self):
        for operation in ("reverify", "correct"):
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                del e["o"].identities[args["identity"]]["history"][-1]["evidence"]["subject_binding"]
                self.assert_refused_unchanged(e, args)

    def test_unapproved_method_or_missing_binding_policy_refuses(self):
        for operation in self.operations:
            for missing in ("method", "policy"):
                with self.subTest(operation=operation, missing=missing):
                    e, args = self.prepare(operation)
                    if missing == "method":
                        e["o"].binding_methods[e["tenant"]] = frozenset()
                    else:
                        p = e["policy"]
                        e["o"].policies[e["tenant"]] = [replace(p, approvals={k: v for k, v in p.approvals.items() if k != "subject_binding"})]
                    self.assert_refused_unchanged(e, args)

    def test_no_accounts_mode_requires_explicit_synthetic_policy_support(self):
        e = fixture()
        o = e["o"]
        o.binding_methods[e["tenant"]] = frozenset({("synthetic-proofing", "account")})
        before = deepcopy((o.identities, o.claims, o.audit_events))
        with self.assertRaises(Refused):
            o.decide(**e["args"])
        self.assertEqual((o.identities, o.claims, o.audit_events), before)
        self.assertFalse(o.current_usable(e["tenant"], e["args"]["identity"], e["policy"].policy_id, now=1001))

    def test_positive_operations_require_consistent_explicit_account_evidence(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                before = deepcopy(e["o"].identities)
                result = e["o"].decide(**args)
                self.assertEqual(result["recorded_decision"], "verified")
                self.assertEqual(result["recorded_revision"], args["expected"] + 1)
                state = e["o"].identities[args["identity"]]
                self.assertEqual(state["student"], "s1")
                self.assertEqual(state["history"][:-1], before.get(args["identity"], {}).get("history", []))
                self.assertEqual(state["history"][-1]["evidence"]["subject_binding"]["evidence"]["user_id"], "subject-user")
                self.assertTrue(e["o"].current_usable(e["tenant"], args["identity"], e["policy"].policy_id,
                                                   now=1001, students=args["students"]))

    def test_historical_retry_after_account_change_is_not_current_usability(self):
        e = fixture(account=True)
        o = e["o"]
        result = o.decide(**e["args"])
        key = (e["tenant"], "s1")
        o.account_associations[key] = replace(o.account_associations[key], auth_id="replacement-auth", revision=2)
        before = deepcopy((o.identities, o.claims, o.audit_events))
        retry = o.decide(**e["args"])
        self.assertTrue(retry["replayed"])
        self.assertEqual(retry["decision_id"], result["decision_id"])
        self.assertEqual((o.identities, o.claims, o.audit_events), before)
        self.assertFalse(o.current_usable(e["tenant"], e["args"]["identity"], e["policy"].policy_id,
                                         now=1001, students=e["args"]["students"]))

    def test_reapproval_alone_does_not_refresh_existing_positive(self):
        e = fixture(account=True)
        o = e["o"]
        o.decide(**e["args"])
        original = deepcopy(o.identities)
        install_binding(e, account=True)
        self.assertFalse(o.current_usable(e["tenant"], e["args"]["identity"], e["policy"].policy_id,
                                         now=1001, students=e["args"]["students"]))
        self.assertEqual(o.identities, original)
        o.decide(**dict(e["args"], operation="reverify", expected=1, request="review-new-proof"))
        self.assertTrue(o.current_usable(e["tenant"], e["args"]["identity"], e["policy"].policy_id,
                                        now=1001, students=e["args"]["students"]))


class NoAccountsDirectoryTests(unittest.TestCase):
    operations = ("verify", "reverify", "correct")

    def prepare(self, operation, *, populated=False):
        e = fixture()
        if populated:
            # A different subject has a valid account while person-1 has valid,
            # current-generation absence proof. No stale-proof setup shortcut.
            self.change(e, [self.association(e, person_key="other-person")], now=30)
            install_binding(e)
        if operation != "verify":
            e["o"].decide(**dict(e["args"], now=900))
            self.assertTrue(e["o"].current_usable(e["tenant"], e["args"]["identity"],
                e["policy"].policy_id, now=901))
        return e, dict(e["args"], operation=operation, request="directory-adversarial",
            expected=0 if operation == "verify" else 1, now=1000)

    def association(self, e, **changes):
        return replace(AccountAssociation(e["tenant"], "person-1", "s1", "subject-user",
                       "subject-auth", 1), **changes)

    def change(self, e, rows, operation="create", now=950, **changes):
        o = e["o"]
        args = dict(actor=e["directory_writer"], tenant=e["tenant"],
            mandate_id=e["directory_mandate"].mandate_id,
            expected_generation=o.directory_heads[e["tenant"]].generation,
            associations=tuple(rows), operation=operation, reason="Synthetic directory lifecycle", now=now)
        return o.record_directory_change(**dict(args, **changes))

    def snapshot(self, o):
        def retained(value):
            # Missing-field faults must be comparable without calling a broken
            # dataclass __eq__; preserve scalar types too (True is not 1).
            if is_dataclass(value):
                return (type(value), retained(vars(value)))
            if isinstance(value, dict):
                return {key: retained(item) for key, item in value.items()}
            if isinstance(value, (tuple, list, set)):
                return type(value)(retained(item) for item in value)
            return (type(value), deepcopy(value))

        return retained((o.identities, o.claims, o.historical_owners, o.receipts,
            o.audit_events, o.subject_bindings, o.binding_history, o.binding_evidence,
            o.account_associations, o.directory_history, o.directory_heads, o.directory_highwater,
            o.directory_baselines, o.directory_initialized))

    def assert_denied(self, e, args, code):
        o = e["o"]
        binding = o.subject_bindings[(e["tenant"], "person-1")]
        # Isolate the directory condition: receipt and approval registries agree.
        self.assertEqual(o.binding_evidence[binding.evidence.evidence_id], binding.evidence)
        self.assertEqual(o.binding_history[binding.binding_id], binding)
        before, denial_count = self.snapshot(o), len(o.denials)
        with self.assertRaisesRegex(Refused, "^" + code + "$"):
            o.decide(**args)
        self.assertEqual(self.snapshot(o), before)
        self.assertEqual(len(o.denials), denial_count + 1)
        self.assertEqual(o.denials[-1], dict(actor=args["actor"].user_id, auth=args["actor"].auth_id,
            institution=e["tenant"], identity=args["identity"], operation=args["operation"],
            request=args["request"], code=code, observed_at=args["now"]))
        self.assertFalse(o.current_usable(e["tenant"], args["identity"], e["policy"].policy_id,
            now=args["now"], students=args.get("students", ())))
        self.assertEqual(self.snapshot(o), before)
        self.assertEqual(len(o.denials), denial_count + 1)

    def test_consistent_attested_generation_allows_all_positive_operations(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                result = e["o"].decide(**args)
                head = e["o"].identities[args["identity"]]["history"][-1]
                receipt = head["evidence"]["subject_binding"]["evidence"]
                self.assertEqual(result["recorded_revision"], args["expected"] + 1)
                self.assertEqual(receipt["directory_generation"], 1)
                self.assertEqual(receipt["directory_baseline_id"], f"directory-baseline:{e['tenant']}")
                self.assertIsNone(receipt["association_revision"])
                self.assertTrue(e["o"].current_usable(e["tenant"], args["identity"],
                    e["policy"].policy_id, now=1001))
                self.assertEqual(len(e["o"].claims), len(e["entry"].raw_values))

    def test_association_creation_invalidates_absence_for_all_operations(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                self.change(e, [self.association(e)])
                self.assert_denied(e, args, "absence_directory_changed")

    def test_creation_then_deletion_does_not_restore_old_absence(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                row = self.association(e)
                self.change(e, [row])
                self.change(e, [], "remove", 951)
                self.assertEqual(e["o"].account_associations, {})
                self.assertEqual(e["o"].directory_highwater[e["tenant"]], 3)
                self.assertEqual(e["o"].directory_history[e["tenant"]][1].associations, (row,))
                self.assert_denied(e, args, "absence_directory_changed")

    def test_reassociation_retains_invalidation_for_original_subject(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                self.change(e, [self.association(e)])
                self.change(e, [self.association(e, person_key="other-person", revision=2)], "reassociate", 951)
                self.assertFalse(any(a.person_key == "person-1" for a in e["o"].account_associations.values()))
                self.assert_denied(e, args, "absence_directory_changed")

    def test_recovery_and_replacement_followed_by_removal_preserve_invalidation(self):
        for operation in self.operations:
            for event in ("recover", "replace"):
                with self.subTest(operation=operation, event=event):
                    e, args = self.prepare(operation)
                    self.change(e, [self.association(e)])
                    self.change(e, [self.association(e, user_id="replacement-user", auth_id="replacement-auth",
                        profile_id="replacement-profile", revision=2)], event, 951)
                    self.change(e, [], "remove", 952)
                    self.assert_denied(e, args, "absence_directory_changed")

    def test_removing_legacy_conflict_cannot_revive_invalidated_absence(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                self.change(e, [self.association(e)])
                rows = [dict(institution_id=e["tenant"], student_id="s1", register_number="0012",
                    university_roll_number="roll-1", user_id="subject-user", auth_user_id="subject-auth",
                    association_revision=1)]
                self.assert_denied(e, dict(args, students=rows), "absence_directory_changed")
                self.change(e, [], "remove", 951)
                self.assert_denied(e, dict(args, students=[]), "absence_directory_changed")

    def test_change_away_and_back_keeps_monotonic_generation(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                initial = e["o"].directory_heads[e["tenant"]]
                self.change(e, [self.association(e)])
                self.change(e, [], "remove", 951)
                head = e["o"].directory_heads[e["tenant"]]
                self.assertEqual(head.associations, initial.associations)
                self.assertGreater(head.generation, initial.generation)
                self.assert_denied(e, args, "absence_directory_changed")

    def test_recovery_with_identical_rows_still_advances_generation(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                self.change(e, [], "recover")
                self.assertEqual(e["o"].directory_heads[e["tenant"]].generation, 2)
                self.assert_denied(e, args, "absence_directory_changed")

    def test_fresh_receipt_cannot_bypass_retained_association_history(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                self.change(e, [self.association(e)])
                self.change(e, [], "remove", 951)
                install_binding(e, collected_at=960, approved_at=970)
                self.assert_denied(e, args, "absence_history_requires_review")

    def test_fresh_receipt_with_inactive_association_still_refuses(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                self.change(e, [self.association(e, active=False)], "deactivate")
                install_binding(e, collected_at=960, approved_at=970)
                self.assert_denied(e, args, "binding_no_accounts")

    def test_missing_or_unreliable_directory_state_fails_closed(self):
        cases = ("head", "history", "highwater", "bootstrap", "baseline", "incomplete", "history_incomplete",
                 "reference_only", "foreign_baseline", "incident", "history_gap", "boolean_generation", "untracked")
        for operation in self.operations:
            for case in cases:
                with self.subTest(operation=operation, case=case):
                    e, args = self.prepare(operation)
                    o, tenant = e["o"], e["tenant"]
                    baseline_id = o.directory_heads[tenant].baseline_id
                    code = "directory_history_unreliable"
                    if case in {"head", "history", "highwater"}:
                        getattr(o, {"head": "directory_heads", "history": "directory_history",
                                    "highwater": "directory_highwater"}[case]).pop(tenant)
                    elif case in {"baseline", "incomplete", "history_incomplete", "reference_only", "foreign_baseline"}:
                        code = "directory_completeness_unresolved"
                        baseline = o.directory_baselines[baseline_id]
                        if case == "baseline":
                            o.directory_baselines.pop(baseline_id)
                        elif case == "reference_only":
                            o.directory_baselines[baseline_id] = "trusted-complete-directory"
                        else:
                            changes = {"incomplete": dict(complete=False), "history_incomplete": dict(history_complete=False),
                                       "foreign_baseline": dict(institution="other")}[case]
                            o.directory_baselines[baseline_id] = replace(baseline, **changes)
                    elif case == "incident":
                        o.directory_unreliable.add(tenant)
                    elif case == "bootstrap":
                        o.directory_initialized.clear()
                    elif case == "history_gap":
                        o.directory_history[tenant] = ()
                    elif case == "boolean_generation":
                        o.directory_highwater[tenant] = True
                    else:
                        code = "directory_snapshot_untracked"
                        o.account_associations[(tenant, "s1")] = self.association(e)
                    self.assert_denied(e, args, code)
                    self.assertIn(tenant, o.directory_unreliable)

    def test_registered_absence_receipt_requires_exact_generation_and_baseline(self):
        for operation in self.operations:
            for change in (dict(directory_generation=None), dict(directory_generation=0),
                           dict(directory_generation=True), dict(directory_generation="1"),
                           dict(directory_generation=2), dict(directory_baseline_id=None),
                           dict(directory_baseline_id="other-baseline")):
                with self.subTest(operation=operation, change=change):
                    e, args = self.prepare(operation)
                    o, key = e["o"], (e["tenant"], "person-1")
                    binding = o.subject_bindings[key]
                    receipt = replace(binding.evidence, **change)
                    binding = replace(binding, evidence=receipt)
                    o.binding_evidence[receipt.evidence_id] = receipt
                    o.binding_history[binding.binding_id] = binding
                    o.subject_bindings[key] = binding
                    self.assert_denied(e, args, "absence_directory_changed")

    def test_directory_rollback_cannot_match_old_receipt_against_highwater(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                self.change(e, [self.association(e)])
                self.change(e, [], "remove", 951)
                o, tenant = e["o"], e["tenant"]
                o.directory_heads[tenant] = o.directory_history[tenant][0]
                o.directory_history[tenant] = o.directory_history[tenant][:1]
                self.assertEqual(o.directory_highwater[tenant], 3)
                self.assert_denied(e, args, "directory_history_unreliable")

    def test_empty_dictionary_and_reference_cannot_bootstrap_completeness(self):
        e = fixture()
        o = Oracle()
        self.assertEqual(o.account_associations, {})
        o.binding_actors = deepcopy(e["o"].binding_actors)
        o.mandates = deepcopy(e["o"].mandates)
        with self.assertRaisesRegex(UnresolvedPolicy, "directory_completeness_unresolved"):
            o.initialize_directory(actor=e["directory_writer"], tenant=e["tenant"],
                mandate_id=e["directory_mandate"].mandate_id, baseline_id="reference-says-complete")
        self.assertEqual(o.directory_heads, {})
        self.assertEqual(o.directory_history, {})
        self.assertEqual(o.audit_events, [])

    def test_directory_writer_authorization_scope_and_revision_denials_preserve_state(self):
        for case in ("unmandated", "forged_auth", "wrong_scope", "revoked", "stale", "foreign_rows"):
            with self.subTest(case=case):
                e = fixture()
                o = e["o"]
                changes = {}
                if case == "unmandated":
                    changes["actor"] = e["admin"]
                elif case == "forged_auth":
                    changes["actor"] = replace(e["directory_writer"], auth_id="forged")
                elif case == "wrong_scope":
                    changes["actor"] = replace(e["directory_writer"], scopes=("other",))
                elif case == "revoked":
                    o.mandate_revocations.add(e["directory_mandate"].mandate_id)
                elif case == "stale":
                    changes["expected_generation"] = 0
                else:
                    changes["associations"] = (self.association(e, institution="other"),)
                before, denials = self.snapshot(o), len(o.denials)
                with self.assertRaises(Refused):
                    self.change(e, [self.association(e)], **changes)
                self.assertEqual(self.snapshot(o), before)
                self.assertEqual(len(o.denials), denials + 1)
                self.assertEqual(o.denials[-1]["operation"], "directory_change")

    def test_directory_reset_and_lost_history_cannot_be_rebootstrapped(self):
        for lost in ("none", "head_history", "head_history_highwater"):
            e = fixture()
            o, tenant = e["o"], e["tenant"]
            if lost != "none":
                o.directory_history.pop(tenant)
                o.directory_heads.pop(tenant)
            if lost == "head_history_highwater":
                o.directory_highwater.pop(tenant)
            with self.subTest(lost=lost), self.assertRaisesRegex(Refused, "directory_reset_forbidden"):
                o.initialize_directory(actor=e["directory_writer"], tenant=tenant,
                    mandate_id=e["directory_mandate"].mandate_id, baseline_id=f"directory-baseline:{tenant}")

    def test_unrelated_institution_does_not_advance_local_generation(self):
        e = fixture()
        e["o"].decide(**e["args"])
        other = fixture(tenant="institution-b", oracle=e["o"])
        self.change(other, [self.association(other)])
        self.assertEqual(e["o"].directory_heads[e["tenant"]].generation, 1)
        self.assertTrue(e["o"].current_usable(e["tenant"], e["args"]["identity"], e["policy"].policy_id, now=1001))

    def test_historical_replay_after_deletion_never_restores_usability(self):
        e = fixture()
        o = e["o"]
        result = o.decide(**e["args"])
        self.change(e, [self.association(e)])
        self.change(e, [], "remove", 951)
        before, denials = self.snapshot(o), len(o.denials)
        replay = o.decide(**e["args"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["decision_id"], result["decision_id"])
        self.assertFalse(o.current_usable(e["tenant"], e["args"]["identity"], e["policy"].policy_id, now=1001))
        self.assertEqual(self.snapshot(o), before)
        self.assertEqual(len(o.denials), denials)

    def test_stale_absence_approval_cannot_replace_current_binding(self):
        for case in ("changed", "missing_history"):
            with self.subTest(case=case):
                e = fixture()
                o = e["o"]
                o.decide(**e["args"])
                binding = o.subject_bindings[(e["tenant"], "person-1")]
                self.change(e, [self.association(e)])
                self.change(e, [], "remove", 951)
                code = "absence_directory_changed"
                if case == "missing_history":
                    o.directory_history.pop(e["tenant"])
                    code = "directory_history_unreliable"
                before, denials = self.snapshot(o), len(o.denials)
                with self.assertRaisesRegex(Refused, "^" + code + "$"):
                    o.approve_binding(actor=e["reviewer"], tenant=e["tenant"],
                        mandate_id=e["review_mandate"].mandate_id, binding_id="stale-directory-reapproval",
                        evidence_id=binding.evidence.evidence_id, policy_id=e["policy"].policy_id, now=1000)
                self.assertEqual(self.snapshot(o), before)
                self.assertEqual(len(o.denials), denials + 1)
                self.assertEqual(o.denials[-1]["operation"], "approve_binding")
                self.assertEqual(o.denials[-1]["code"], code)
                self.assertFalse(o.current_usable(e["tenant"], e["args"]["identity"], e["policy"].policy_id, now=1001))

    def test_unrelated_subject_change_requires_fresh_proof_and_explicit_positive(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                self.change(e, [self.association(e, person_key="other-person")])
                self.assert_denied(e, args, "absence_directory_changed")
                install_binding(e, collected_at=960, approved_at=970)
                self.assertFalse(e["o"].current_usable(e["tenant"], args["identity"], e["policy"].policy_id, now=999))
                result = e["o"].decide(**dict(args, request="new-generation-explicit-decision"))
                self.assertEqual(result["recorded_revision"], args["expected"] + 1)
                head = e["o"].identities[args["identity"]]["history"][-1]
                self.assertEqual(head["evidence"]["subject_binding"]["evidence"]["directory_generation"], 2)
                self.assertTrue(e["o"].current_usable(e["tenant"], args["identity"], e["policy"].policy_id, now=1001))

    def test_directory_writer_revocation_blocks_all_absence_positives_and_usability(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                e["o"].mandate_revocations.add(e["directory_mandate"].mandate_id)
                self.assert_denied(e, args, "mandate")

    def test_missing_directory_governance_cannot_enable_absence_decisions(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                policy = e["policy"]
                e["o"].policies[e["tenant"]] = [replace(policy,
                    approvals={k: v for k, v in policy.approvals.items() if k != "absence_directory"})]
                self.assert_denied(e, args, "policy")

    def test_observed_untracked_change_cannot_heal_after_direct_row_removal(self):
        for operation in self.operations:
            for detection in ("decision", "read"):
                with self.subTest(operation=operation, detection=detection):
                    e, args = self.prepare(operation)
                    o, tenant = e["o"], e["tenant"]
                    # Bypass the proposed writer deliberately: detect and latch loss
                    # of authoritative continuity, never infer a trusted revision.
                    o.account_associations[(tenant, "s1")] = self.association(e)
                    if detection == "read":
                        # Initial verify has no recorded head, so use a recorded
                        # baseline decision to exercise the read detector itself.
                        if operation == "verify":
                            o.account_associations.clear()
                            o.decide(**dict(e["args"], now=900))
                            o.account_associations[(tenant, "s1")] = self.association(e)
                            args = dict(args, operation="reverify", expected=1)
                        self.assertFalse(o.current_usable(tenant, args["identity"], e["policy"].policy_id, now=999))
                        self.assert_denied(e, args, "directory_history_unreliable")
                    else:
                        self.assert_denied(e, args, "directory_snapshot_untracked")
                    self.assertIn(tenant, o.directory_unreliable)
                    o.account_associations.clear()
                    self.assert_denied(e, args, "directory_history_unreliable")

    def test_restoring_missing_history_does_not_clear_observed_integrity_incident(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                o, tenant = e["o"], e["tenant"]
                history = o.directory_history.pop(tenant)
                self.assert_denied(e, args, "directory_history_unreliable")
                o.directory_history[tenant] = history
                self.assert_denied(e, args, "directory_history_unreliable")

    def test_account_revision_cannot_be_reset_by_new_directory_writer(self):
        e = fixture(account=True)
        o = e["o"]
        o.decide(**e["args"])
        row = self.association(e)
        self.change(e, [replace(row, user_id="other-user", auth_id="other-auth", revision=2)], "replace")
        before, denials = self.snapshot(o), len(o.denials)
        with self.assertRaisesRegex(Refused, "^directory_association_revision$"):
            self.change(e, [row], "recover", 951)
        self.assertEqual(self.snapshot(o), before)
        self.assertEqual(len(o.denials), denials + 1)
        self.assertEqual(o.denials[-1]["code"], "directory_association_revision")
        self.change(e, [replace(row, revision=3)], "recover", 951)
        self.assertFalse(o.current_usable(e["tenant"], e["args"]["identity"], e["policy"].policy_id,
            now=1001, students=[dict(e["args"]["students"][0], association_revision=3)]))


    def assert_transition(self, e, rows, operation, now):
        """Prove the writer transition itself, independently of stale-proof refusal."""
        o, tenant = e["o"], e["tenant"]
        protected = deepcopy((o.identities, o.claims, o.historical_owners, o.receipts,
            o.subject_bindings, o.binding_history, o.binding_evidence, o.directory_baselines,
            o.directory_initialized, o.directory_unreliable))
        history, audits, denials = deepcopy(o.directory_history[tenant]), deepcopy(o.audit_events), len(o.denials)
        generation = o.directory_highwater[tenant]
        event = self.change(e, rows, operation, now)
        self.assertIs(type(event.generation), int)
        self.assertEqual(event.generation, generation + 1)
        self.assertEqual(o.directory_heads[tenant], event)
        self.assertEqual(o.directory_highwater[tenant], generation + 1)
        self.assertEqual(o.directory_history[tenant][:-1], history)
        self.assertEqual(len(o.directory_history[tenant]), len(history) + 1)
        self.assertEqual(event.associations, tuple(sorted(rows, key=lambda a: a.profile_id)))
        self.assertEqual(event.operation, operation)
        self.assertEqual((event.writer_user_id, event.writer_auth_id, event.writer_mandate_id, event.recorded_at),
            (e["directory_writer"].user_id, e["directory_writer"].auth_id, e["directory_mandate"].mandate_id, now))
        self.assertEqual(o.audit_events[:-1], audits)
        self.assertEqual(o.audit_events[-1][0:2], ("directory_change", tenant))
        self.assertEqual(o.audit_events[-1][2]["generation"], generation + 1)
        self.assertEqual(len(o.denials), denials)
        self.assertEqual((o.identities, o.claims, o.historical_owners, o.receipts,
            o.subject_bindings, o.binding_history, o.binding_evidence, o.directory_baselines,
            o.directory_initialized, o.directory_unreliable), protected)
        return event

    def replace_registered_receipt(self, e, **changes):
        o, key = e["o"], (e["tenant"], "person-1")
        binding = o.subject_bindings[key]
        receipt = replace(binding.evidence, **changes)
        binding = replace(binding, evidence=receipt)
        o.binding_evidence[receipt.evidence_id] = receipt
        o.binding_history[binding.binding_id] = binding
        o.subject_bindings[key] = binding

    def test_head_generation_is_checked_independently_before_python_equality(self):
        for operation in self.operations:
            for value in (True, False, "1", None, -1, 0, 2, 1.0):
                with self.subTest(operation=operation, value=value, value_type=type(value).__name__):
                    e, args = self.prepare(operation)
                    o, tenant = e["o"], e["tenant"]
                    untouched = deepcopy((o.directory_history, o.directory_highwater, o.directory_baselines,
                        o.directory_initialized, o.binding_evidence, o.binding_history, o.subject_bindings))
                    o.directory_heads[tenant] = replace(o.directory_heads[tenant], generation=value)
                    self.assertEqual((o.directory_history, o.directory_highwater, o.directory_baselines,
                        o.directory_initialized, o.binding_evidence, o.binding_history, o.subject_bindings), untouched)
                    self.assert_denied(e, args, "directory_history_unreliable")
                    self.assertIn(tenant, o.directory_unreliable)

    def assert_head_associations_refused(self, e, args, associations, code="directory_snapshot"):
        o, tenant = e["o"], e["tenant"]
        original = o._directory_state(tenant)
        binding = o.subject_bindings[(tenant, "person-1")]
        self.assertEqual(binding.evidence.directory_generation, original.generation)
        self.assertNotIn(tenant, o.directory_unreliable)
        before = self.snapshot(o)
        # Corrupt ONLY the independent head, keeping journal, highwater, live
        # rows, evidence/approval registries and historical decisions intact.
        o.directory_heads[tenant] = replace(original, associations=associations)
        corrupted = self.snapshot(o)
        self.assertEqual(corrupted[:10], before[:10])
        self.assertEqual(corrupted[11:], before[11:])
        self.assert_denied(e, args, code)
        self.assertIn(tenant, o.directory_unreliable)
        o.directory_heads[tenant] = original
        self.assertEqual(self.snapshot(o), before)
        self.assert_denied(e, args, "directory_history_unreliable")
        self.assertIn(tenant, o.directory_unreliable)

    def test_head_association_revision_requires_actual_positive_integer(self):
        for operation in self.operations:
            for value in (True, False, 1.0, 1.5, "1", None, 0, -1):
                with self.subTest(operation=operation, value=value, value_type=type(value).__name__):
                    e, args = self.prepare(operation, populated=True)
                    row = e["o"].directory_heads[e["tenant"]].associations[0]
                    self.assertIs(type(row.revision), int)
                    self.assertEqual(row.revision, 1)
                    self.assert_head_associations_refused(e, args, (replace(row, revision=value),))

    def test_false_and_zero_association_revisions_cannot_authenticate_each_other(self):
        e, args = self.prepare("reverify", populated=True)
        o, tenant = e["o"], e["tenant"]
        head = o.directory_heads[tenant]
        row = head.associations[0]
        # Zero is itself invalid, so this equality trap is additional malformed
        # authoritative state coverage, not a purported valid revision-zero row.
        zero = replace(row, revision=0)
        false = replace(row, revision=False)
        self.assertEqual(false, zero)
        o.directory_history[tenant] = o.directory_history[tenant][:-1] + (
            replace(head, associations=(zero,)),)
        o.account_associations[(tenant, row.profile_id)] = zero
        o.directory_heads[tenant] = replace(head, associations=(false,))
        self.assert_denied(e, args, "directory_snapshot")
        self.assertIn(tenant, o.directory_unreliable)

    def test_head_association_fields_and_container_are_independently_validated(self):
        for operation in self.operations:
            for field in ("institution", "person_key", "profile_id", "user_id", "auth_id", "active"):
                values = (None, "", " ", True, 1, 1.0, "x" * 257) if field != "active" else (None, 0, 1, "true")
                for value in values:
                    with self.subTest(operation=operation, field=field, value=value):
                        e, args = self.prepare(operation, populated=True)
                        row = e["o"].directory_heads[e["tenant"]].associations[0]
                        self.assert_head_associations_refused(e, args, (replace(row, **{field: value}),))
            for container in (None, [], ({},), (None,)):
                with self.subTest(operation=operation, container=container):
                    e, args = self.prepare(operation, populated=True)
                    self.assert_head_associations_refused(e, args, container)

    def test_missing_head_and_association_fields_refuse_without_attribute_errors(self):
        for operation in self.operations:
            for field in ("institution", "person_key", "profile_id", "user_id", "auth_id", "revision", "active"):
                with self.subTest(operation=operation, association_field=field):
                    e, args = self.prepare(operation, populated=True)
                    row = deepcopy(e["o"].directory_heads[e["tenant"]].associations[0])
                    object.__delattr__(row, field)
                    self.assert_head_associations_refused(e, args, (row,))
            for field in ("institution", "baseline_id", "generation", "associations", "writer_user_id",
                          "writer_auth_id", "writer_mandate_id", "recorded_at", "operation", "reason"):
                with self.subTest(operation=operation, head_field=field):
                    e, args = self.prepare(operation, populated=True)
                    o, tenant = e["o"], e["tenant"]
                    head = deepcopy(o.directory_heads[tenant])
                    object.__delattr__(head, field)
                    o.directory_heads[tenant] = head
                    self.assert_denied(e, args, "directory_history_unreliable")
                    self.assertIn(tenant, o.directory_unreliable)

    def test_well_typed_head_association_substitution_contradicts_valid_journal(self):
        for operation in self.operations:
            for field in ("institution", "person_key", "profile_id", "user_id", "auth_id", "revision", "active"):
                with self.subTest(operation=operation, field=field):
                    e, args = self.prepare(operation, populated=True)
                    row = e["o"].directory_heads[e["tenant"]].associations[0]
                    value = 2 if field == "revision" else False if field == "active" else "substituted"
                    code = "directory_snapshot" if field == "institution" else "directory_history_unreliable"
                    self.assert_head_associations_refused(e, args, (replace(row, **{field: value}),), code)

    def test_head_association_fault_latches_on_current_read_before_any_decision_attempt(self):
        for missing in (False, True):
            with self.subTest(missing_revision=missing):
                e, args = self.prepare("reverify", populated=True)
                o, tenant = e["o"], e["tenant"]
                self.assertTrue(o.current_usable(tenant, args["identity"], e["policy"].policy_id, now=999))
                head = o.directory_heads[tenant]
                row = replace(head.associations[0], revision=True)
                if missing:
                    object.__delattr__(row, "revision")
                o.directory_heads[tenant] = replace(head, associations=(row,))
                before, denials = self.snapshot(o), deepcopy(o.denials)
                self.assertFalse(o.current_usable(tenant, args["identity"], e["policy"].policy_id, now=999))
                self.assertIn(tenant, o.directory_unreliable)
                self.assertEqual(self.snapshot(o), before)
                self.assertEqual(o.denials, denials)
                o.directory_heads[tenant] = head
                self.assert_denied(e, args, "directory_history_unreliable")

    def test_invalid_absence_receipt_does_not_mark_valid_populated_directory_corrupt(self):
        e, args = self.prepare("reverify", populated=True)
        o, tenant = e["o"], e["tenant"]
        self.replace_registered_receipt(e, directory_generation=True)
        self.assert_denied(e, args, "absence_directory_changed")
        self.assertNotIn(tenant, o.directory_unreliable)
        self.assertEqual(o._directory_state(tenant), o.directory_heads[tenant])

    def test_head_only_corruption_is_detected_by_current_read_without_a_decision_attempt(self):
        for value in (True, False, "1", None, -1, 0, 2, 1.0):
            with self.subTest(value=value, value_type=type(value).__name__):
                e, args = self.prepare("reverify")
                o, tenant = e["o"], e["tenant"]
                original = o.directory_heads[tenant]
                o.directory_heads[tenant] = replace(original, generation=value)
                before, denials = self.snapshot(o), len(o.denials)
                self.assertFalse(o.current_usable(tenant, args["identity"], e["policy"].policy_id, now=999))
                self.assertIn(tenant, o.directory_unreliable)
                self.assertEqual(self.snapshot(o), before)
                self.assertEqual(len(o.denials), denials)  # A read latches an incident, not a decision denial.
                o.directory_heads[tenant] = original
                self.assert_denied(e, args, "directory_history_unreliable")

    def test_each_retained_generation_field_rejects_malformed_values(self):
        for operation in self.operations:
            for field in ("journal", "highwater", "receipt"):
                for value in (True, False, "1", None, -1, 0, 2, 1.0):
                    with self.subTest(operation=operation, field=field, value=value, value_type=type(value).__name__):
                        e, args = self.prepare(operation)
                        o, tenant = e["o"], e["tenant"]
                        if field == "journal":
                            o.directory_history[tenant] = (replace(o.directory_history[tenant][0], generation=value),)
                        elif field == "highwater":
                            o.directory_highwater[tenant] = value
                        else:
                            self.replace_registered_receipt(e, directory_generation=value)
                        code = "absence_directory_changed" if field == "receipt" else "directory_history_unreliable"
                        self.assert_denied(e, args, code)
                        self.assertEqual(tenant in o.directory_unreliable, field != "receipt")

    def test_writer_expected_generation_rejects_boolean_and_invalid_values(self):
        for value in (True, False, "1", None, -1, 0, 2, 1.0):
            with self.subTest(value=value, value_type=type(value).__name__):
                e = fixture()
                o, tenant = e["o"], e["tenant"]
                before, denials = self.snapshot(o), len(o.denials)
                with self.assertRaisesRegex(Refused, "^directory_revision_conflict$"):
                    self.change(e, [], expected_generation=value)
                self.assertEqual(self.snapshot(o), before)
                self.assertEqual(len(o.denials), denials + 1)
                self.assertEqual(o.denials[-1], dict(actor=e["directory_writer"].user_id,
                    auth=e["directory_writer"].auth_id, institution=tenant,
                    operation="directory_change", code="directory_revision_conflict", observed_at=950))
                self.assertNotIn(tenant, o.directory_unreliable)

    def test_current_generation_receipt_cannot_predate_its_directory_state(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                # Source accepted at 20; directory baseline at 25. All registries
                # agree and source/time validity passes before the directory test.
                self.replace_registered_receipt(e, collected_at=20)
                self.assert_denied(e, args, "absence_directory_changed")
                self.assertNotIn(e["tenant"], e["o"].directory_unreliable)

    def test_restore_previous_snapshot_advances_generation_and_preserves_tombstones(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                baseline_rows = e["o"].directory_heads[e["tenant"]].associations
                self.assert_transition(e, [self.association(e)], "create", 950)
                self.assert_transition(e, baseline_rows, "restore", 951)
                self.assertEqual(e["o"].directory_highwater[e["tenant"]], 3)
                self.assert_denied(e, args, "absence_directory_changed")

    def test_restore_identical_snapshot_invalidates_previously_usable_evidence(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                # No preceding creation: this restore is the sole invalidating event.
                self.assert_transition(e, [], "restore", 950)
                self.assert_denied(e, args, "absence_directory_changed")

    def assert_restore_revision_denied(self, e, rows, now):
        o, tenant = e["o"], e["tenant"]
        # Valid authority, expected generation, chronology and row schema: this
        # attempt must reach restore's historical association-revision guard.
        self.assertEqual(o._directory_state(tenant), o.directory_heads[tenant])
        self.assertEqual(o._directory_rows(tenant, tuple(rows)), tuple(rows))
        before, denials = self.snapshot(o), len(o.denials)
        with self.assertRaisesRegex(Refused, "^directory_association_revision$"):
            self.change(e, rows, "restore", now)
        self.assertEqual(self.snapshot(o), before)
        self.assertNotIn(tenant, o.directory_unreliable)
        self.assertEqual(len(o.denials), denials + 1)
        self.assertEqual(o.denials[-1], dict(actor=e["directory_writer"].user_id,
            auth=e["directory_writer"].auth_id, institution=tenant, operation="directory_change",
            code="directory_association_revision", observed_at=now))

    def test_populated_identical_restore_requires_fresh_revision_and_invalidates_absence(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation, populated=True)
                o, tenant = e["o"], e["tenant"]
                row = o.directory_heads[tenant].associations[0]
                self.assertEqual(row.revision, 1)
                # Even an unchanged populated tuple must advance its revision
                # for restore, unlike an unchanged row in an ordinary create.
                self.assert_restore_revision_denied(e, [row], 950)
                if operation != "verify":
                    self.assertTrue(o.current_usable(tenant, args["identity"], e["policy"].policy_id, now=950))
                self.assert_transition(e, [replace(row, revision=2)], "restore", 951)
                self.assertEqual(o.directory_highwater[tenant], 3)
                self.assert_denied(e, args, "absence_directory_changed")
                self.assertNotIn(tenant, o.directory_unreliable)

    def test_populated_restore_of_prior_account_tuple_enforces_retained_revision_maximum(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation, populated=True)
                o, tenant = e["o"], e["tenant"]
                old = o.directory_heads[tenant].associations[0]
                newer = replace(old, profile_id="new-profile", user_id="new-user", auth_id="new-auth", revision=4)
                self.assert_transition(e, [newer], "replace", 950)
                # Old row is absent from live state but remains in the journal.
                # Same subject links its history to the newer account tuple.
                self.assert_restore_revision_denied(e, [old], 951)
                self.assert_restore_revision_denied(e, [replace(old, revision=4)], 951)
                self.assert_transition(e, [replace(old, revision=5)], "restore", 952)
                self.assertEqual(o.directory_highwater[tenant], 4)
                self.assertEqual(o.directory_history[tenant][1].associations, (old,))
                self.assertEqual(o.directory_history[tenant][2].associations, (newer,))
                self.assert_denied(e, args, "absence_directory_changed")
                self.assertNotIn(tenant, o.directory_unreliable)

    def test_highwater_rollback_alone_latches_and_cannot_heal_when_restored(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                self.assert_transition(e, [self.association(e)], "create", 950)
                self.assert_transition(e, [], "remove", 951)
                o, tenant = e["o"], e["tenant"]
                head, history = deepcopy(o.directory_heads[tenant]), deepcopy(o.directory_history[tenant])
                o.directory_highwater[tenant] = 1
                self.assert_denied(e, args, "directory_history_unreliable")
                self.assertEqual((o.directory_heads[tenant], o.directory_history[tenant]), (head, history))
                o.directory_highwater[tenant] = 3
                self.assert_denied(e, args, "directory_history_unreliable")
                self.assertIn(tenant, o.directory_unreliable)

    def test_mixed_restoration_of_directory_baseline_and_receipt_fails_closed(self):
        cases = (
            (("head",), "directory_history_unreliable"),
            (("history",), "directory_history_unreliable"),
            (("highwater",), "directory_history_unreliable"),
            (("head", "history"), "directory_history_unreliable"),
            (("head", "highwater"), "directory_history_unreliable"),
            (("history", "highwater"), "directory_history_unreliable"),
            (("baseline", "receipt"), "absence_directory_changed"),
            (("head", "history", "highwater"), "directory_snapshot_untracked"),
            (("head", "history", "highwater", "baseline", "receipt"), "directory_snapshot_untracked"),
            (("head", "history", "highwater", "baseline", "live"), "absence_directory_changed"),
        )
        for operation in self.operations:
            for fields, code in cases:
                with self.subTest(operation=operation, restored=fields):
                    e, args = self.prepare(operation)
                    o, tenant = e["o"], e["tenant"]
                    saved = deepcopy(dict(head=o.directory_heads[tenant], history=o.directory_history[tenant],
                        highwater=o.directory_highwater[tenant], baseline=o.directory_baselines,
                        receipt=(o.binding_evidence, o.binding_history, o.subject_bindings), live=o.account_associations))
                    self.assert_transition(e, [self.association(e, person_key="other-person")], "create", 950)
                    install_binding(e, collected_at=960, approved_at=970)
                    for field in fields:
                        if field == "receipt":
                            o.binding_evidence, o.binding_history, o.subject_bindings = deepcopy(saved[field])
                        elif field == "baseline":
                            o.directory_baselines = deepcopy(saved[field])
                        elif field == "live":
                            o.account_associations = deepcopy(saved[field])
                        else:
                            getattr(o, {"head": "directory_heads", "history": "directory_history",
                                        "highwater": "directory_highwater"}[field])[tenant] = deepcopy(saved[field])
                    self.assert_denied(e, args, code)
                    if code != "absence_directory_changed":
                        self.assertIn(tenant, o.directory_unreliable)

    def test_coherent_total_model_restore_is_an_undetectable_trust_boundary(self):
        e = fixture()
        o, tenant = e["o"], e["tenant"]
        result = o.decide(**e["args"])
        saved = deepcopy(o.__dict__)
        self.assert_transition(e, [self.association(e)], "create", 1001)
        self.assert_transition(e, [], "remove", 1002)
        args = dict(e["args"], operation="reverify", expected=1, request="before-total-restore", now=1003)
        self.assert_denied(e, args, "absence_directory_changed")
        # Deliberately simulate privileged rollback of EVERY model-held input,
        # including audit/denials and continuity markers. This is NOT an ordinary
        # operation and NOT a security guarantee. No independent witness survives.
        o.__dict__.clear()
        o.__dict__.update(deepcopy(saved))
        self.assertEqual(o.__dict__, saved)
        self.assertTrue(o.current_usable(tenant, e["args"]["identity"], e["policy"].policy_id, now=1004))
        replay = o.decide(**e["args"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["decision_id"], result["decision_id"])
        self.assertEqual(o.__dict__, saved)
        # A synthetic externally supplied unreliability signal forces refusal;
        # this does not implement or prove the eventual external authority.
        o.directory_unreliable.add(tenant)
        self.assert_denied(e, dict(args, request="external-continuity-unknown", now=1005),
                           "directory_history_unreliable")

    def test_all_ordinary_writer_operations_refuse_after_latched_incident(self):
        for operation in self.operations:
            for directory_operation in ("create", "remove", "reassociate", "recover", "replace", "activate", "deactivate", "restore"):
                with self.subTest(operation=operation, directory_operation=directory_operation):
                    e, args = self.prepare(operation)
                    o, tenant = e["o"], e["tenant"]
                    head = o.directory_heads[tenant]
                    o.directory_heads[tenant] = replace(head, generation=True)
                    self.assert_denied(e, args, "directory_history_unreliable")
                    o.directory_heads[tenant] = head  # Cleanup cannot clear the separate incident.
                    before, denials = self.snapshot(o), len(o.denials)
                    with self.assertRaisesRegex(Refused, "^directory_history_unreliable$"):
                        self.change(e, [], directory_operation, 1001)
                    self.assertEqual(self.snapshot(o), before)
                    self.assertEqual(len(o.denials), denials + 1)
                    self.assertEqual(o.denials[-1], dict(actor=e["directory_writer"].user_id,
                        auth=e["directory_writer"].auth_id, institution=tenant, operation="directory_change",
                        code="directory_history_unreliable", observed_at=1001))
                    self.assertIn(tenant, o.directory_unreliable)
                    self.assert_denied(e, dict(args, request="after-denied-cleanup", now=1002),
                                       "directory_history_unreliable")

    def test_bootstrap_cannot_clear_incident_even_when_other_markers_are_removed(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                o, tenant = e["o"], e["tenant"]
                o.directory_history.pop(tenant)
                self.assert_denied(e, args, "directory_history_unreliable")
                o.directory_heads.pop(tenant)
                o.directory_highwater.pop(tenant)
                o.directory_initialized.clear()
                o.account_associations.clear()
                # Complete baseline and live writer authority remain valid; only
                # the latched incident prevents otherwise empty-state bootstrap.
                before, denials = self.snapshot(o), len(o.denials)
                baseline_id = f"directory-baseline:{tenant}"
                with self.assertRaisesRegex(Refused, "^directory_reset_forbidden$"):
                    o.initialize_directory(actor=e["directory_writer"], tenant=tenant,
                        mandate_id=e["directory_mandate"].mandate_id, baseline_id=baseline_id, now=1001)
                self.assertEqual(self.snapshot(o), before)
                self.assertEqual(len(o.denials), denials + 1)
                self.assertEqual(o.denials[-1], dict(actor=e["directory_writer"].user_id,
                    auth=e["directory_writer"].auth_id, institution=tenant, operation="directory_initialize",
                    baseline_id=baseline_id, code="directory_reset_forbidden", observed_at=1001))
                self.assertIn(tenant, o.directory_unreliable)
                self.assert_denied(e, dict(args, request="after-bootstrap-denial", now=1002),
                                   "directory_history_unreliable")

    def test_remove_and_recreate_association_keeps_old_proof_invalid(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                e, args = self.prepare(operation)
                row = self.association(e)
                self.assert_transition(e, [row], "create", 950)
                self.assert_transition(e, [], "remove", 951)
                self.assert_transition(e, [replace(row, revision=2)], "create", 952)
                self.assert_transition(e, [], "remove", 953)
                self.assertEqual(e["o"].directory_highwater[e["tenant"]], 5)
                self.assert_denied(e, args, "absence_directory_changed")
                install_binding(e, collected_at=960, approved_at=970)
                self.assert_denied(e, args, "absence_history_requires_review")

    def test_each_reassociation_variant_invalidates_current_matching_absence_evidence(self):
        for operation in self.operations:
            for variant in ("same_account", "different_account", "different_auth"):
                with self.subTest(operation=operation, variant=variant):
                    e, args = self.prepare(operation)
                    self.assert_transition(e, [self.association(e, person_key="other-person")], "create", 950)
                    install_binding(e, collected_at=960, approved_at=970)
                    result = e["o"].decide(**dict(args, request="fresh-before-reassociation", now=980))
                    self.assertTrue(e["o"].current_usable(e["tenant"], args["identity"], e["policy"].policy_id, now=981))
                    changes = dict(revision=2)
                    if variant == "different_account":
                        changes.update(user_id="replacement-user", auth_id="replacement-auth", profile_id="replacement-profile")
                    elif variant == "different_auth":
                        changes["auth_id"] = "replacement-auth"
                    self.assert_transition(e, [self.association(e, **changes)], "reassociate", 990)
                    self.assert_denied(e, dict(args, expected=result["recorded_revision"],
                        operation="reverify" if operation == "verify" else operation,
                        request="after-reassociation", now=1000), "absence_directory_changed")

    def test_recovery_and_replacement_advance_each_generation_before_legacy_cleanup(self):
        for operation in self.operations:
            for directory_operation in ("recover", "replace"):
                with self.subTest(operation=operation, directory_operation=directory_operation):
                    e, args = self.prepare(operation)
                    self.assert_transition(e, [self.association(e)], "create", 950)
                    row = self.association(e, revision=2, auth_id="replacement-auth",
                        user_id="subject-user" if directory_operation == "recover" else "replacement-user")
                    self.assert_transition(e, [row], directory_operation, 951)
                    students = [dict(institution_id=e["tenant"], student_id="s1", register_number="0012",
                        university_roll_number="roll-1", user_id=row.user_id, auth_user_id=row.auth_id,
                        association_revision=2)]
                    self.assert_denied(e, dict(args, students=students), "absence_directory_changed")
                    self.assert_transition(e, [], "remove", 952)
                    self.assert_denied(e, dict(args, students=[]), "absence_directory_changed")
                    self.assertEqual(e["o"].directory_highwater[e["tenant"]], 4)


    def prepare_account(self, operation):
        e = fixture(account=True)
        if operation != "verify":
            e["o"].decide(**dict(e["args"], now=900))
            self.assertTrue(e["o"].current_usable(e["tenant"], e["args"]["identity"],
                e["policy"].policy_id, now=901, students=e["args"]["students"]))
        return e, dict(e["args"], operation=operation, request="strict-account",
            expected=0 if operation == "verify" else 1, now=1000)

    def assert_live_fault(self, e, args, fault, code="directory_snapshot"):
        o, tenant = e["o"], e["tenant"]
        self.assertEqual(o._directory_state(tenant), o.directory_heads[tenant])
        key = (tenant, "s1")
        original, healthy = o.account_associations[key], self.snapshot(o)
        o.account_associations[key] = fault
        self.assert_denied(e, args, code)
        self.assertIn(tenant, o.directory_unreliable)
        o.account_associations[key] = original
        self.assertEqual(self.snapshot(o), healthy)
        # Repairing live fields never clears an observed authoritative incident.
        self.assert_denied(e, args, "directory_history_unreliable")
        self.assertIn(tenant, o.directory_unreliable)

    def assert_profile_fault(self, e, args, rows, code="binding_profile"):
        o, tenant = e["o"], e["tenant"]
        self.assertEqual(o._directory_state(tenant), o.directory_heads[tenant])
        self.assert_denied(e, dict(args, students=rows), code)
        self.assertNotIn(tenant, o.directory_unreliable)
        self.assertEqual(o._directory_state(tenant), o.directory_heads[tenant])
        if args["operation"] != "verify":
            self.assertTrue(o.current_usable(tenant, args["identity"], e["policy"].policy_id,
                now=args["now"], students=args["students"]))
        # Only an explicit positive command with the valid original profile succeeds.
        result = o.decide(**args)
        self.assertEqual(result["recorded_revision"], args["expected"] + 1)
        self.assertTrue(o.current_usable(tenant, args["identity"], e["policy"].policy_id,
            now=args["now"], students=args["students"]))

    def test_account_live_revision_types_refuse_before_equality_and_latch(self):
        for operation in self.operations:
            for value in (True, False, 1.0, 1.5, "1", None, 0, -1):
                with self.subTest(operation=operation, value=value, value_type=type(value).__name__):
                    e, args = self.prepare_account(operation)
                    row = e["o"].account_associations[(e["tenant"], "s1")]
                    self.assert_live_fault(e, args, replace(row, revision=value))

    def test_account_live_activity_requires_actual_boolean(self):
        for operation in self.operations:
            for value in (None, 0, 1, 1.0, "true"):
                with self.subTest(operation=operation, value=value, value_type=type(value).__name__):
                    e, args = self.prepare_account(operation)
                    row = e["o"].account_associations[(e["tenant"], "s1")]
                    self.assert_live_fault(e, args, replace(row, active=value))

    def test_account_live_identifiers_are_independently_validated(self):
        for operation in self.operations:
            for field in ("institution", "person_key", "profile_id", "user_id", "auth_id"):
                for value in (None, "", " ", True, 1, 1.0, "x" * 257):
                    with self.subTest(operation=operation, field=field, value=value):
                        e, args = self.prepare_account(operation)
                        row = e["o"].account_associations[(e["tenant"], "s1")]
                        self.assert_live_fault(e, args, replace(row, **{field: value}))

    def test_account_profile_revision_requires_actual_positive_integer(self):
        for operation in self.operations:
            for value in (True, False, 1.0, 1.5, "1", None, 0, -1):
                with self.subTest(operation=operation, value=value, value_type=type(value).__name__):
                    e, args = self.prepare_account(operation)
                    rows = [dict(args["students"][0], association_revision=value)]
                    self.assert_profile_fault(e, args, rows)

    def test_account_profile_identifiers_are_validated_before_tuple_comparison(self):
        for operation in self.operations:
            for field in ("institution_id", "student_id", "user_id", "auth_user_id"):
                for value in (None, "", " ", True, 1, 1.0, "x" * 257):
                    with self.subTest(operation=operation, field=field, value=value):
                        e, args = self.prepare_account(operation)
                        self.assert_profile_fault(e, args, [dict(args["students"][0], **{field: value})])

    def test_account_profile_missing_fields_and_malformed_objects_refuse(self):
        for operation in self.operations:
            for field in ("institution_id", "student_id", "user_id", "auth_user_id", "association_revision"):
                with self.subTest(operation=operation, missing=field):
                    e, args = self.prepare_account(operation)
                    row = dict(args["students"][0])
                    del row[field]
                    self.assert_profile_fault(e, args, [row])
            for rows in (None, {}, [None], [()], ["profile"]):
                with self.subTest(operation=operation, rows=rows):
                    e, args = self.prepare_account(operation)
                    self.assert_profile_fault(e, args, rows)

    def test_account_well_typed_profile_mismatches_do_not_mark_directory_corrupt(self):
        for operation in self.operations:
            for field in ("institution_id", "student_id", "user_id", "auth_user_id", "association_revision"):
                with self.subTest(operation=operation, field=field):
                    e, args = self.prepare_account(operation)
                    value = 2 if field == "association_revision" else "different"
                    code = "binding_profile" if field in {"institution_id", "student_id"} else "binding_account_ownership"
                    self.assert_profile_fault(e, args, [dict(args["students"][0], **{field: value})], code)

    def test_account_well_typed_untracked_live_changes_latch(self):
        for operation in self.operations:
            for field in ("institution", "person_key", "profile_id", "user_id", "auth_id", "revision", "active"):
                with self.subTest(operation=operation, field=field):
                    e, args = self.prepare_account(operation)
                    row = e["o"].account_associations[(e["tenant"], "s1")]
                    value = 2 if field == "revision" else False if field == "active" else "different"
                    code = "directory_snapshot" if field in {"institution", "profile_id"} else "directory_snapshot_untracked"
                    self.assert_live_fault(e, args, replace(row, **{field: value}), code)

    def test_account_valid_tracked_tuple_changes_reach_ownership_check_without_latching(self):
        for operation in self.operations:
            for field in ("person_key", "profile_id", "user_id", "auth_id", "revision", "active"):
                with self.subTest(operation=operation, field=field):
                    e, args = self.prepare_account(operation)
                    o, tenant = e["o"], e["tenant"]
                    row = o.account_associations[(tenant, "s1")]
                    changes = {field: False if field == "active" else "different", "revision": 2}
                    self.assert_transition(e, [replace(row, **changes)], "replace", 950)
                    self.assertEqual(o._directory_state(tenant), o.directory_heads[tenant])
                    self.assert_denied(e, args, "binding_account_ownership")
                    self.assertNotIn(tenant, o.directory_unreliable)

    def test_live_missing_fields_refuse_and_latch_in_both_binding_modes(self):
        for account in (False, True):
            for operation in self.operations:
                for field in ("institution", "person_key", "profile_id", "user_id", "auth_id", "revision", "active"):
                    with self.subTest(account=account, operation=operation, missing=field):
                        e, args = (self.prepare_account(operation) if account
                                   else self.prepare(operation, populated=True))
                        row = deepcopy(e["o"].account_associations[(e["tenant"], "s1")])
                        object.__delattr__(row, field)
                        self.assert_live_fault(e, args, row)

    def test_live_malformed_row_objects_refuse_and_latch_in_both_binding_modes(self):
        for account in (False, True):
            for operation in self.operations:
                for row in (None, {}, (), [], ("malformed",), "association", 1):
                    with self.subTest(account=account, operation=operation, row=row):
                        e, args = (self.prepare_account(operation) if account
                                   else self.prepare(operation, populated=True))
                        self.assert_live_fault(e, args, row)

    def test_current_read_detects_live_fault_before_decision_and_repair_cannot_heal(self):
        for account in (False, True):
            for fault in ("institution", "revision", "object", "boolean_revision", "numeric_active"):
                with self.subTest(account=account, fault=fault):
                    e, args = (self.prepare_account("reverify") if account
                               else self.prepare("reverify", populated=True))
                    o, tenant = e["o"], e["tenant"]
                    self.assertTrue(o.current_usable(tenant, args["identity"], e["policy"].policy_id,
                        now=999, students=args.get("students", ())))
                    key = (tenant, "s1")
                    original = o.account_associations[key]
                    row = deepcopy(original)
                    if fault in {"institution", "revision"}:
                        object.__delattr__(row, fault)
                    elif fault == "object":
                        row = None
                    else:
                        row = replace(row, **({"revision": True} if fault == "boolean_revision" else {"active": 1}))
                    o.account_associations[key] = row
                    before, denials = self.snapshot(o), deepcopy(o.denials)
                    self.assertFalse(o.current_usable(tenant, args["identity"], e["policy"].policy_id,
                        now=999, students=args.get("students", ())))
                    self.assertEqual(self.snapshot(o), before)
                    self.assertEqual(o.denials, denials)
                    self.assertIn(tenant, o.directory_unreliable)
                    o.account_associations[key] = original
                    self.assertFalse(o.current_usable(tenant, args["identity"], e["policy"].policy_id,
                        now=999, students=args.get("students", ())))
                    self.assert_denied(e, args, "directory_history_unreliable")

    def test_registered_malformed_account_receipt_does_not_latch_healthy_directory(self):
        for operation in self.operations:
            for value in (True, False, 1.0, 1.5, "1", None, 0, -1):
                with self.subTest(operation=operation, value=value, value_type=type(value).__name__):
                    e, args = self.prepare_account(operation)
                    o, tenant = e["o"], e["tenant"]
                    self.replace_registered_receipt(e, association_revision=value)
                    self.assert_denied(e, args, "binding_incomplete")
                    self.assertNotIn(tenant, o.directory_unreliable)
                    self.assertEqual(o._directory_state(tenant), o.directory_heads[tenant])

    def test_malformed_writer_payload_does_not_latch_healthy_account_directory(self):
        for operation in self.operations:
            for fault in ("revision", "active", "missing_institution", "object"):
                with self.subTest(operation=operation, fault=fault):
                    e, args = self.prepare_account(operation)
                    o, tenant = e["o"], e["tenant"]
                    row = deepcopy(o.account_associations[(tenant, "s1")])
                    if fault == "missing_institution":
                        object.__delattr__(row, "institution")
                    elif fault == "object":
                        row = None
                    else:
                        row = replace(row, **{fault: True if fault == "revision" else 1})
                    before, denials = self.snapshot(o), len(o.denials)
                    with self.assertRaisesRegex(Refused, "^directory_snapshot$"):
                        self.change(e, [row], "restore", 950)
                    self.assertEqual(self.snapshot(o), before)
                    self.assertNotIn(tenant, o.directory_unreliable)
                    self.assertEqual(len(o.denials), denials + 1)
                    self.assertEqual(o.denials[-1], dict(actor=e["directory_writer"].user_id,
                        auth=e["directory_writer"].auth_id, institution=tenant,
                        operation="directory_change", code="directory_snapshot", observed_at=950))
                    self.assertEqual(o.current_usable(tenant, args["identity"], e["policy"].policy_id,
                        now=999, students=args["students"]), operation != "verify")

    def test_account_historical_replay_after_live_integrity_fault_is_history_only(self):
        e = fixture(account=True)
        o, tenant = e["o"], e["tenant"]
        result = o.decide(**e["args"])
        row = deepcopy(o.account_associations[(tenant, "s1")])
        object.__delattr__(row, "institution")
        o.account_associations[(tenant, "s1")] = row
        self.assertFalse(o.current_usable(tenant, e["args"]["identity"], e["policy"].policy_id,
            now=1001, students=e["args"]["students"]))
        self.assertIn(tenant, o.directory_unreliable)
        before, denials = self.snapshot(o), deepcopy(o.denials)
        replay = o.decide(**e["args"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["decision_id"], result["decision_id"])
        self.assertEqual(self.snapshot(o), before)
        self.assertEqual(o.denials, denials)
        self.assertFalse(o.current_usable(tenant, e["args"]["identity"], e["policy"].policy_id,
            now=1001, students=e["args"]["students"]))


    def retained_slot(self, e, location):
        o, tenant = e["o"], e["tenant"]
        binding = o.subject_bindings[(tenant, "person-1")]
        if location == "proof":
            return o.binding_evidence, binding.evidence.evidence_id
        if location == "approval":
            return o.binding_history, binding.binding_id
        if location == "current":
            return o.subject_bindings, (tenant, "person-1")
        history = o.identities[e["args"]["identity"]]["history"]
        return history[-1 if location == "head" else 0]["evidence"], "subject_binding"

    def corrupt_retained(self, e, location, path, value=None, *, missing=False):
        store, key = self.retained_slot(e, location)
        original = store[key]
        root = deepcopy(original)
        if location == "proof":
            path = path[1:]  # Proof registry contains the receipt, not its approval.
        node = root
        for name in path[:-1]:
            node = node[name] if isinstance(node, dict) else getattr(node, name)
        if isinstance(node, dict):
            if missing:
                del node[path[-1]]
            else:
                node[path[-1]] = value
        elif missing:
            object.__delattr__(node, path[-1])
        else:
            object.__setattr__(node, path[-1], value)
        store[key] = root
        return store, key, original

    def assert_copy_refused(self, e, args, code=None):
        """Do not authenticate malformed copies with equality in the assertion."""
        o, tenant = e["o"], e["tenant"]
        before, denied = self.snapshot(o), len(o.denials)
        with self.assertRaises(Refused) as refusal:
            o.decide(**args)
        if code is not None:
            self.assertEqual(str(refusal.exception), code)
        self.assertEqual(self.snapshot(o), before)
        self.assertEqual(o.denials[-1], dict(actor=args["actor"].user_id, auth=args["actor"].auth_id,
            institution=tenant, identity=args["identity"], operation=args["operation"],
            request=args["request"], code=str(refusal.exception), observed_at=args["now"]))
        self.assertEqual(len(o.denials), denied + 1)
        self.assertFalse(o.current_usable(tenant, args["identity"], e["policy"].policy_id,
            now=args["now"], students=args.get("students", ()), rosters=args.get("rosters", ())))
        self.assertEqual(self.snapshot(o), before)
        self.assertEqual(len(o.denials), denied + 1)
        self.assertNotIn(tenant, o.directory_unreliable)
        self.assertEqual(o._directory_state(tenant), o.directory_heads[tenant])

    def check_retained_revisions(self, location):
        operations = self.operations if location != "head" else ("reverify", "correct")
        for operation in operations:
            for value in (True, False, 1.0, 1.5, "1", None, 0, -1):
                with self.subTest(location=location, operation=operation, value=value, kind=type(value).__name__):
                    e, args = self.prepare_account(operation)
                    self.corrupt_retained(e, location, ("evidence", "association_revision"), value)
                    self.assert_copy_refused(e, args)

    def test_retained_proof_revision_is_validated_independently(self):
        self.check_retained_revisions("proof")

    def test_retained_approval_revision_is_validated_independently(self):
        self.check_retained_revisions("approval")

    def test_current_binding_revision_is_validated_independently(self):
        self.check_retained_revisions("current")

    def test_historical_head_revision_is_validated_independently(self):
        self.check_retained_revisions("head")

    def test_non_head_historical_revision_blocks_reads_and_new_positives(self):
        for operation in ("reverify", "correct"):
            for value in (True, 1.0):
                with self.subTest(operation=operation, value=value, kind=type(value).__name__):
                    e, args = self.prepare_account(operation)
                    o = e["o"]
                    o.decide(**args)
                    self.assertTrue(o.current_usable(e["tenant"], args["identity"], e["policy"].policy_id,
                        now=1000, students=args["students"]))
                    self.corrupt_retained(e, "older", ("evidence", "association_revision"), value)
                    self.assert_copy_refused(e, dict(args, expected=2, request="after-older-corruption"),
                        "historical_binding_unresolved")

    def test_retained_security_fields_are_checked_before_equality(self):
        faults = (("complete", 1), ("collected_at", 40.0), ("valid_until", float(10**12)),
                  ("mode", []), ("institution", None), ("person_key", True),
                  ("profile_id", []), ("user_id", {}), ("auth_id", 1),
                  ("source_id", []), ("entry_id", {}), ("evidence_id", []),
                  ("establisher_user_id", []), ("establisher_auth_id", {}),
                  ("establisher_mandate_id", None), ("method", []), ("provenance_reference", ""))
        for location in ("proof", "approval", "current", "head"):
            for field, value in faults:
                with self.subTest(location=location, field=field):
                    e, args = self.prepare_account("reverify")
                    self.corrupt_retained(e, location, ("evidence", field), value)
                    self.assert_copy_refused(e, args)
        for location in ("approval", "current", "head"):
            for field, value in (("approved_at", 50.0), ("approved_at", True),
                                 ("binding_id", []), ("reviewer_user_id", {}),
                                 ("reviewer_auth_id", None), ("reviewer_mandate_id", []), ("policy_id", {})):
                with self.subTest(location=location, field=field):
                    e, args = self.prepare_account("reverify")
                    self.corrupt_retained(e, location, (field,), value)
                    self.assert_copy_refused(e, args)

    def test_each_retained_copy_requires_all_declared_fields(self):
        for location in ("proof", "approval", "current", "head"):
            for field in vars(fixture(account=True)["o"].subject_bindings[("institution-a", "person-1")].evidence):
                with self.subTest(location=location, receipt_missing=field):
                    e, args = self.prepare_account("reverify")
                    self.corrupt_retained(e, location, ("evidence", field), missing=True)
                    self.assert_copy_refused(e, args)
        for location in ("approval", "current", "head"):
            for field in ("binding_id", "evidence", "reviewer_user_id", "reviewer_auth_id",
                          "reviewer_mandate_id", "approved_at", "policy_id"):
                with self.subTest(location=location, approval_missing=field):
                    e, args = self.prepare_account("reverify")
                    self.corrupt_retained(e, location, (field,), missing=True)
                    self.assert_copy_refused(e, args)

    def test_malformed_retained_copy_objects_refuse_without_directory_incident(self):
        for location in ("proof", "approval", "current", "head"):
            for value in (None, {}, [], (), "receipt", 1, True):
                with self.subTest(location=location, kind=type(value).__name__):
                    e, args = self.prepare_account("reverify")
                    store, key = self.retained_slot(e, location)
                    store[key] = value
                    self.assert_copy_refused(e, args)

    def test_absence_generation_is_checked_in_each_retained_copy(self):
        for location in ("proof", "approval", "current", "head"):
            for value in (True, 1.0):
                with self.subTest(location=location, value=value, kind=type(value).__name__):
                    e, args = self.prepare("reverify")
                    self.corrupt_retained(e, location, ("evidence", "directory_generation"), value)
                    self.assert_copy_refused(e, args)

    def test_historical_replay_remains_history_only_after_retained_proof_fault(self):
        e = fixture(account=True)
        o, tenant = e["o"], e["tenant"]
        result = o.decide(**e["args"])
        store, key, original = self.corrupt_retained(e, "proof", ("evidence", "association_revision"), True)
        self.assertFalse(o.current_usable(tenant, e["args"]["identity"], e["policy"].policy_id,
            now=1001, students=e["args"]["students"]))
        before, denials = self.snapshot(o), deepcopy(o.denials)
        replay = o.decide(**e["args"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["decision_id"], result["decision_id"])
        self.assertEqual(self.snapshot(o), before)
        self.assertEqual(o.denials, denials)
        self.assertNotIn(tenant, o.directory_unreliable)
        store[key] = original
        self.assertTrue(o.current_usable(tenant, e["args"]["identity"], e["policy"].policy_id,
            now=1001, students=e["args"]["students"]))

    def test_fresh_correction_preserves_expired_but_well_formed_historical_evidence(self):
        e = fixture(account=True)
        o, tenant = e["o"], e["tenant"]
        install_binding(e, account=True, valid_until=950)
        o.decide(**dict(e["args"], now=900))
        original = deepcopy(o.identities[e["args"]["identity"]]["history"][0])
        self.assertFalse(o.current_usable(tenant, e["args"]["identity"], e["policy"].policy_id,
            now=1000, students=e["args"]["students"]))
        install_binding(e, account=True)
        result = o.decide(**dict(e["args"], operation="correct", expected=1, request="fresh-correction"))
        self.assertEqual(result["recorded_revision"], 2)
        self.assertEqual(o.identities[e["args"]["identity"]]["history"][0], original)
        self.assertTrue(o.current_usable(tenant, e["args"]["identity"], e["policy"].policy_id,
            now=1001, students=e["args"]["students"]))

    def assert_baseline_fault(self, e, args, fault, code=None):
        o, tenant = e["o"], e["tenant"]
        key = o.directory_heads[tenant].baseline_id
        original = o.directory_baselines[key]
        o.directory_baselines[key] = fault
        if code is None:
            before, denied = self.snapshot(o), len(o.denials)
            with self.assertRaises(Refused) as refusal:
                o.decide(**args)
            self.assertEqual(self.snapshot(o), before)
            self.assertEqual(len(o.denials), denied + 1)
            self.assertEqual(o.denials[-1], dict(actor=args["actor"].user_id, auth=args["actor"].auth_id,
                institution=tenant, identity=args["identity"], operation=args["operation"],
                request=args["request"], code=str(refusal.exception), observed_at=args["now"]))
        else:
            self.assert_denied(e, args, code)
        self.assertIn(tenant, o.directory_unreliable)
        o.directory_baselines[key] = original
        self.assert_denied(e, args, "directory_history_unreliable")
        self.assertIn(tenant, o.directory_unreliable)

    def test_baseline_requires_each_declared_field_in_both_modes(self):
        for account in (False, True):
            for operation in self.operations:
                e0 = fixture(account=account)
                baseline = next(iter(e0["o"].directory_baselines.values()))
                for field in vars(baseline):
                    with self.subTest(account=account, operation=operation, missing=field):
                        e, args = self.prepare_account(operation) if account else self.prepare(operation)
                        fault = deepcopy(next(iter(e["o"].directory_baselines.values())))
                        object.__delattr__(fault, field)
                        self.assert_baseline_fault(e, args, fault, "directory_completeness_unresolved")

    def test_malformed_baseline_objects_refuse_and_latch_in_both_modes(self):
        for account in (False, True):
            for operation in self.operations:
                for fault in (None, {}, [], (), "baseline", 1, True):
                    with self.subTest(account=account, operation=operation, kind=type(fault).__name__):
                        e, args = self.prepare_account(operation) if account else self.prepare(operation)
                        self.assert_baseline_fault(e, args, fault, "directory_completeness_unresolved")

    def test_baseline_field_types_refuse_before_authority_and_row_operations(self):
        for account in (False, True):
            for field, value in (("writer_user_id", []), ("writer_auth_id", {}),
                                 ("writer_mandate_id", None), ("institution", 1),
                                 ("baseline_id", []), ("provenance_reference", {}),
                                 ("observed_at", 25.0), ("observed_at", True),
                                 ("complete", 1), ("history_complete", 1), ("associations", [])):
                with self.subTest(account=account, field=field):
                    e, args = self.prepare_account("reverify") if account else self.prepare("reverify")
                    baseline = next(iter(e["o"].directory_baselines.values()))
                    self.assert_baseline_fault(e, args, replace(baseline, **{field: value}))

    def test_read_first_baseline_detection_survives_field_or_object_repair(self):
        for account in (False, True):
            for field in ("institution", "associations", "writer_user_id", "object"):
                with self.subTest(account=account, field=field):
                    e, args = self.prepare_account("reverify") if account else self.prepare("reverify")
                    o, tenant = e["o"], e["tenant"]
                    key = o.directory_heads[tenant].baseline_id
                    original = o.directory_baselines[key]
                    fault = deepcopy(original)
                    if field == "object":
                        fault = None
                    else:
                        object.__delattr__(fault, field)
                    o.directory_baselines[key] = fault
                    before, denials = self.snapshot(o), deepcopy(o.denials)
                    self.assertFalse(o.current_usable(tenant, args["identity"], e["policy"].policy_id,
                        now=999, students=args.get("students", ())))
                    self.assertEqual(self.snapshot(o), before)
                    self.assertEqual(o.denials, denials)
                    self.assertIn(tenant, o.directory_unreliable)
                    o.directory_baselines[key] = original
                    self.assertFalse(o.current_usable(tenant, args["identity"], e["policy"].policy_id,
                        now=999, students=args.get("students", ())))
                    self.assert_denied(e, args, "directory_history_unreliable")

    def test_request_or_receipt_errors_do_not_fabricate_baseline_detection(self):
        for account in (False, True):
            for error_kind in ("request", "receipt"):
                with self.subTest(account=account, error_kind=error_kind):
                    e, args = self.prepare_account("reverify") if account else self.prepare("reverify")
                    o, tenant = e["o"], e["tenant"]
                    key = o.directory_heads[tenant].baseline_id
                    original = o.directory_baselines[key]
                    fault = deepcopy(original)
                    object.__delattr__(fault, "institution")
                    o.directory_baselines[key] = fault
                    if error_kind == "request":
                        args["expected"] = True
                    else:
                        field = "association_revision" if account else "directory_generation"
                        self.corrupt_retained(e, "proof", ("evidence", field), True)
                    before, count = self.snapshot(o), len(o.denials)
                    with self.assertRaises(Refused):
                        o.decide(**args)
                    self.assertEqual(self.snapshot(o), before)
                    self.assertEqual(len(o.denials), count + 1)
                    self.assertNotIn(tenant, o.directory_unreliable)
                    o.directory_baselines[key] = original
                    self.assertEqual(o._directory_state(tenant), o.directory_heads[tenant])

    def test_profile_identifier_types_refuse_before_string_operations(self):
        for operation in self.operations:
            for field in ("register_number", "university_roll_number"):
                for value in (12, 1.0, True, False, [], {}, (), b"0012"):
                    with self.subTest(operation=operation, field=field, kind=type(value).__name__):
                        e, args = self.prepare_account(operation)
                        self.assert_profile_fault(e, args, [dict(args["students"][0], **{field: value})])

    def test_missing_profile_register_stays_refused_and_null_roll_stays_optional(self):
        for operation in self.operations:
            for value in (None, "", " \t"):
                with self.subTest(operation=operation, register=value):
                    e, args = self.prepare_account(operation)
                    self.assert_profile_fault(e, args, [dict(args["students"][0], register_number=value)],
                        "policy_or_identifier" if value == " \t" else "identity_conflict")
            e, args = self.prepare_account(operation)
            args["students"] = [dict(args["students"][0], university_roll_number=None)]
            result = e["o"].decide(**args)
            self.assertEqual(result["recorded_revision"], args["expected"] + 1)
            self.assertTrue(e["o"].current_usable(e["tenant"], args["identity"], e["policy"].policy_id,
                now=1001, students=args["students"]))

    def test_roster_identifier_types_refuse_without_directory_incident(self):
        for operation in self.operations:
            for field in ("register_number", "university_roll_number"):
                for value in (12, 1.0, True, False, [], {}, (), b"0012"):
                    with self.subTest(operation=operation, field=field, kind=type(value).__name__):
                        e, args = self.prepare_account(operation)
                        roster = dict(institution_id=e["tenant"], register_number="0012", university_roll_number="roll-1")
                        roster[field] = value
                        self.assert_copy_refused(e, dict(args, rosters=[roster]), "roster_conflict")
        e, args = self.prepare_account("reverify")
        roster = dict(institution_id=e["tenant"], register_number=None, university_roll_number="roll-1")
        self.assert_copy_refused(e, dict(args, rosters=[roster]), "roster_conflict")

    def test_unselected_profile_identifiers_are_validated_in_both_modes(self):
        for account in (False, True):
            for field in ("register_number", "university_roll_number"):
                with self.subTest(account=account, field=field):
                    e, args = self.prepare_account("reverify") if account else self.prepare("reverify")
                    other = dict(institution_id=e["tenant"], student_id="unrelated", register_number="other", university_roll_number=None)
                    other[field] = []
                    self.assert_copy_refused(e, dict(args, students=list(args.get("students", ())) + [other]), "binding_profile")

    def assert_command_input_refused(self, e, args, code):
        o, tenant = e["o"], e["tenant"]
        before, denials = self.snapshot(o), len(o.denials)
        with self.assertRaisesRegex(Refused, "^" + code + "$"):
            o.decide(**args)
        self.assertEqual(self.snapshot(o), before)
        self.assertEqual(len(o.denials), denials + 1)
        self.assertEqual(o.denials[-1], dict(actor=args["actor"].user_id, auth=args["actor"].auth_id,
            institution=tenant, identity=args["identity"], operation=args["operation"], request=args["request"],
            code=code, observed_at=args["now"]))
        self.assertNotIn(tenant, o.directory_unreliable)
        self.assertEqual(o.current_usable(tenant, args["identity"], e["policy"].policy_id,
            now=args["now"], students=e["args"].get("students", ())), bool(o.identities))

    def test_decision_expected_revision_requires_actual_nonnegative_integer(self):
        for operation in ("verify", "reverify", "correct", "withdraw"):
            for value in (True, False, 0.0, 1.0, 1.5, "0", "1", -1, None, [], {}):
                with self.subTest(operation=operation, value=value, kind=type(value).__name__):
                    e, args = self.prepare_account("reverify" if operation == "withdraw" else operation)
                    args.update(operation=operation, expected=value)
                    if operation == "withdraw":
                        args.update(policy_id=None, source_id=None, entry_id=None, student=None)
                    self.assert_command_input_refused(e, args, "request")

    def test_malformed_profile_selection_never_falls_back_to_retained_target(self):
        for operation in self.operations:
            for value in ("", " ", False, True, 0, 1, 1.0, [], {}, (), "x" * 257):
                with self.subTest(operation=operation, value=value, kind=type(value).__name__):
                    e, args = self.prepare_account(operation)
                    self.assert_command_input_refused(e, dict(args, student=value), "binding_profile")

    def test_explicit_none_preserves_valid_retained_account_selection(self):
        for operation in ("reverify", "correct"):
            with self.subTest(operation=operation):
                e, args = self.prepare_account(operation)
                result = e["o"].decide(**dict(args, student=None))
                self.assertEqual(result["recorded_revision"], 2)
                self.assertEqual(e["o"].identities[args["identity"]]["student"], "s1")
                self.assertTrue(e["o"].current_usable(e["tenant"], args["identity"], e["policy"].policy_id,
                    now=1001, students=args["students"]))

    def test_permission_expected_revision_also_rejects_boolean_substitutes(self):
        for value in (True, False, 0.0, 1.0, "1", -1, None, [], {}):
            with self.subTest(value=value, kind=type(value).__name__):
                e = fixture(account=True)
                o = e["o"]
                before = deepcopy((o.permission_events, o.audit_events, o.receipts))
                with self.assertRaisesRegex(Refused, "^request$"):
                    o.manage_permission(actor=e["grantor"], tenant=e["tenant"],
                        mandate_id=e["grant_mandate"].mandate_id, target=e["staff"], expected=value,
                        request="malformed-permission-revision", grant=False, reason="Synthetic malformed revision")
                self.assertEqual((o.permission_events, o.audit_events, o.receipts), before)
                self.assertNotIn(e["tenant"], o.directory_unreliable)


class NormalizationAndBoundaryTests(unittest.TestCase):
    def test_normalization_mechanisms_do_not_select_owner_policy(self):
        self.assertEqual(normalize(" 0012 ", "ascii_trim"), "0012")
        self.assertEqual(normalize(" 0012 ", "exact"), " 0012 ")
        self.assertEqual(normalize("ab-é", "ascii_trim_upper"), "AB-é")
        for value, rule in ((12, "exact"), (" \t", "exact"), ("x"*257, "exact"), ("12", "unknown")):
            with self.subTest(value=value, rule=rule), self.assertRaises(Refused):
                normalize(value, rule)

    def test_unicode_policy_is_not_invented_by_ascii_mechanisms(self):
        self.assertNotEqual(normalize("００１２", "ascii_trim"), "0012")
        self.assertNotEqual(normalize("e\u0301", "exact"), normalize("é", "exact"))
        self.assertEqual(normalize("\u00a00012\u00a0", "ascii_trim"), "\u00a00012\u00a0")
        # These are mechanism limits, not approval to admit these characters.

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.sql = (cls.root / "proposed_migration.sql").read_text(encoding="utf-8")
        cls.code = re.sub(r"--[^\n]*", "", cls.sql)

    def test_execution_stop_and_artifact_count(self):
        self.assertLess(self.sql.index("RAISE EXCEPTION 'DESIGN_ONLY_NOT_AUTHORIZED'"), self.sql.index("CREATE SCHEMA"))
        self.assertNotIn("supabase/migrations", str(self.root).replace("\\", "/"))
        files = [p for p in self.root.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
        self.assertEqual(len(files), 7)

    def test_no_legacy_state_writes_or_excluded_artifacts(self):
        tables = r"(?:students|users|user_roles|roles|role_permissions|user_permission_grants|faculty_attendance_rosters|student_attendance|platform_admin_invitations)"
        forbidden = rf"\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM|TRUNCATE(?:\s+TABLE)?)\s+(?:public\.)?{tables}\b"
        self.assertIsNone(re.search(forbidden, self.code, re.I))
        self.assertNotIn("b05_", self.code.lower())
        self.assertNotIn("e23_", self.code.lower())
        self.assertNotRegex(self.code, r"(?i)CREATE\s+OR\s+REPLACE\s+FUNCTION")
        # This static guard is not a SQL parser or proof of deployed behavior.

    def test_no_configuration_or_permission_assignment_seeds(self):
        for table in ("policies", "authority_mandates", "register_versions", "register_entries"):
            self.assertIsNone(re.search(rf"INSERT\s+INTO\s+academic_verification\.{table}\b", self.code, re.I))
        self.assertIn("academic_identity.verify", self.sql)
        self.assertNotIn("JOIN public.role_permissions", self.sql)

    def test_positive_subject_guard_remains_until_control_is_designed(self):
        body = self.code.split("CREATE FUNCTION public.record_academic_identity_verification(", 1)[1]
        body = body.split("CREATE FUNCTION public.record_academic_candidate_finding(", 1)[0]
        self.assertRegex(body, r"ELSE\s+RAISE EXCEPTION 'AV_SELF_APPROVAL_CONTROL_UNRESOLVED' USING ERRCODE='42501';\s+policy:=")
        self.assertLess(body.index("IF answer IS NOT NULL THEN RETURN answer;"),
                        body.index("RAISE EXCEPTION 'AV_SELF_APPROVAL_CONTROL_UNRESOLVED'"))
        # Reading text does not execute SQL or verify this function's behavior.

    def test_new_boundaries_are_explicit_in_artifacts(self):
        for needle in ("sha256", "storage_version_id", "source_as_of", "source_invalidations",
                       "candidate_findings", "authority_revocations", "permission_events",
                       "LOCK TABLE public.user_roles,public.roles IN SHARE MODE",
                       "observed_students", "observed_rosters", "governance_approvals"):
            self.assertIn(needle, self.sql)
        for filename in ("README.md", "rpc_contract.md", "offline_test_plan.md", "postgres_integration_tests.md"):
            text = (self.root / filename).read_text(encoding="utf-8").lower()
            self.assertIn("freshness", text)
            self.assertIn("normalization", text)
            self.assertIn("unverified", text)

    def test_oracle_imports_no_application_database_or_network_modules(self):
        for filename in ("contract_oracle.py", "test_contract_oracle.py"):
            text = (self.root / "draft_tests" / filename).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"^\s*(?:from|import)\s+(?:app|supabase|psycopg|requests|httpx)\b", text, re.M))


if __name__ == "__main__":
    unittest.main()

