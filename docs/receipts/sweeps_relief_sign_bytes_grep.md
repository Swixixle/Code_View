# Receipt: Sweeps_Relief `sign_bytes` static trace bug


**Date:** 2026-04-21


**Reporter:** Alex Maksimovich


**Context:** Code_View verification run against Sweeps_Relief during Sweeps pipeline audit.


## Observation


Code_View's archaeology `/trace` endpoint returned empty `callers` and `called_by` arrays for multiple crypto entities in Sweeps_Relief, despite unambiguous cross-module call sites verifiable by `grep`.


## Entities affected in this reproduction


- `sign_bytes` at `src/sweeps_relief/signer/ed25519.py:66` (entity `ent_fee3b0de06f6503a936f8480a1496535`)


- `verify_envelope` at `src/sweeps_relief/envelope/verifier.py:53` (entity `ent_753b76eda5a669327b84f96c67e13984`)


- `build_policy_artifact` at `src/sweeps_relief/policy/build.py:25` (entity `ent_b7623f63832b93d91419509cd060ab53`)


- `verify_bytes` at `src/sweeps_relief/signer/ed25519.py` (entity `ent_e1176af32b60ec96ef1980b6639333a3`)


All returned `callers: []` and `called_by: []` from `/api/analysis/entity/{id}/trace`.


## Ground truth (grep transcript)


The following grep commands, run from `~/Sweeps_Relief`, show that these entities are in fact called from multiple modules within the same repo.


### Who calls `sign_bytes`


```


./src/sweeps_relief/signer/__init__.py:6:    sign_bytes,


./src/sweeps_relief/signer/__init__.py:15:    "sign_bytes",


./src/sweeps_relief/signer/ed25519.py:66:def sign_bytes(private_key: Ed25519PrivateKey, message: bytes) -> bytes:


./src/sweeps_relief/logger/events.py:19:from sweeps_relief.signer.ed25519 import sign_bytes, verify_bytes


./src/sweeps_relief/logger/events.py:74:    sig = sign_bytes(private_key, to_sign)


./src/sweeps_relief/logger/events.py:106:    sig = sign_bytes(private_key, to_sign)


./src/sweeps_relief/discovery/candidates.py:13:from sweeps_relief.signer.ed25519 import sign_bytes


./src/sweeps_relief/discovery/candidates.py:53:        sig = sign_bytes(private_key, canon)


./src/sweeps_relief/policy/build.py:15:from sweeps_relief.signer.ed25519 import sign_bytes, verify_bytes


./src/sweeps_relief/policy/build.py:32:    sig = sign_bytes(private_key, body)


```


### Who calls `verify_envelope`


```


./src/sweeps_relief/envelope/ingest.py:12:from .verifier import verify_envelope


./src/sweeps_relief/envelope/ingest.py:47:    return verify_envelope(doc, trust_store, expected_artifact_type="intel_snapshot")


./src/sweeps_relief/envelope/ingest.py:58:    return verify_envelope(doc, trust_store, expected_artifact_type="intel_block_candidates")


```


### Who calls `build_policy_artifact`


```


./src/sweeps_relief/cli.py:19:    build_policy_artifact,


./src/sweeps_relief/cli.py:131:    artifact = build_policy_artifact(content, key, signer_kid=kid)


```


## Expected `/trace` output for `sign_bytes`


At minimum, `called_by` should include entities from:


- `src/sweeps_relief/logger/events.py` (lines 74, 106)


- `src/sweeps_relief/discovery/candidates.py` (line 53)


- `src/sweeps_relief/policy/build.py` (line 32)


Relative-import re-exports in `signer/__init__.py` are acceptable to include or exclude as long as the behavior is consistent.


## Why this matters


The whole value of archaeology over `grep -r` is that it resolves names across scope and module boundaries. If `trace` returns empty callers for unambiguous `from X import Y` plus direct-call patterns, the reachability signal is not trustworthy — and the downstream reviewer view of any orient dossier (see `docs/orient_dossier.md`) cannot distinguish "genuinely orphaned" from "static analyzer missed the edge." The orient dossier's reviewer view will need to hedge any such finding until this is fixed.


## Fix reference


See the accompanying PR. Regression test is at `backend/tests/archaeology/test_cross_module_trace.py`.


Commit this file first, before making any code changes. It's the reason for the rest of the PR.
