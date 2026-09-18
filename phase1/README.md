# Phase 1 — Offline Machine Identity

This phase creates a deterministic local machine fingerprint for the future
offline licensing system.

## What it does

On Windows, the diagnostic utility reads these values through read-only CIM
queries:

- System UUID
- Motherboard serial
- BIOS serial
- System manufacturer
- System model

Available values are normalized and combined into canonical text, then hashed
with SHA-256 to produce the machine fingerprint.

The application does not contact a server and this phase contains no license
signing/private key.

## Run

From this directory:

```powershell
python machine_info.py
```

Run tests:

```powershell
python -m pytest -q
```

## Important security/design notes

1. The SHA-256 fingerprint is not a secret. It is an identifier.
2. The Phase 1 fingerprint policy is intentionally not final until it has been
   tested against the actual target hardware.
3. Do not distribute any private signing key with the application.
4. Do not use the fingerprint alone as a license. Phase 2/3 will bind it to a
   digitally signed license.
5. Hardware identifiers can sometimes be unavailable, duplicated, changed by
   firmware/vendor tooling, or virtualized. This must be tested on the actual
   deployment population.
6. A client-side Python executable cannot be made absolutely tamper-proof.
   Later phases will add cryptographic verification and tamper-resistance
   measures.

## Suggested Phase 1 acceptance criteria

- Same physical machine produces the same fingerprint across repeated runs.
- Two intended target machines produce different fingerprints.
- Missing/placeholder identifiers do not crash collection.
- The application can operate completely offline.
- No secret/private key exists in this phase.
