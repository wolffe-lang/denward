# Implementation plan

## Scope

Build a static wolf command for PAX with native macOS arm64 and Linux endpoints. SSH to a Mac's encrypted volume is the primary store; a separate disk is the second copy. A fresh journalled PAX install precedes restoration. No raw-disk image, filesystem conversion, web store, preserved same-disk partition or installer UI is part of the initial tool.

The accepted pipeline is a bounded archive stream, a standard encrypted-format provider, then an untrusted byte store. Both the archive writer and every store take explicit stream interfaces. The selected profile is ordinary binary age v1 with two native X25519 recovery recipients; see encryption-v1. This scaffold refuses the unavailable provider. Plaintext requires both explicit flags on held local media and is never allowed over SSH. The first real backup is gated on qualified entropy, independent review, interoperability and external key recovery.

## Sequence

1. **Scaffold and contracts:** pins, licences, frozen CLI/archive/store/recovery specifications, refusal-only command, asserted tests and CI files. Keep unpublished shared dependency audit records outside this tree. A private local build cannot establish hosted PR-event evidence.
2. **Backup, verify and Mac-first SSH together:** manifest-derived inventory and safe-object archive writer; bounded ciphertext digest/receipt validation; restricted receive/commit/send endpoint on macOS arm64 and Linux; macOS OpenSSH fixture and PAX's shipped client. Do not wait for restore before qualifying the primary store. Bring in the standard encryption provider as soon as its own format and independent review clear; never make plaintext an implicit normal path.
3. **Local restore and PAX prerequisites:** semantic accounts and ownership maps, configuration three-way decisions, host-key identity, exact metadata and sparse-file capability, confined descriptor-relative actions, journal detection and maintenance boot gate. Qualify actual journalled fresh installation separately from image-created ext3 roots.
4. **Reinstall qualification:** image A to fresh journalled image B, independent file/metadata checker, each selected store, two verified copies, corrupt/truncated backup refusals and power cuts during backup, restore and recovery. Repeat a completed restore and preserve later local edits as conflicts.
5. **Later:** installer wrapper around the same engine. Web storage, same-disk partition preservation, compression, incremental retention and transfer resume each need a scoped follow-up; none is inferred from SSH or resumable restore.

## Required proof

Named rows cover scope, physical archive framing, logical metadata/link/sparse fidelity, disk stores, SSH backpressure/status/failure, before-write integrity refusal, A-to-B restoration, backup cuts, restore/recovery cuts, repeatability, old-version compatibility, secrets and the actual journalled installer. GNU tar and bsdtar are black-box physical-container contrasts, not logical restoration oracles. The independent restored-tree checker does not reuse the restore engine.

## Current stop conditions

The public archive core is now pinned at paxage `2c69152ba9aa760ec5104b65a23ef961bfa83368`, with exact source/licence provenance and explicit caller-admitted profiles. The internal safe-object writer/physical inspector is the first archive-path checkpoint of step 2. It does not import package extraction policy as logical recovery authority or enable a production backup profile. An internal schema-directed manifest reader now validates strict encoding and manifest-only relations at explicit test admission limits; it is not a complete logical verifier. Restricted-control validation and physical/object-content binding, source inventory generation, the measured combined entry ceiling, encryption/controller and receive/commit/SSH integration remain unfinished. The inventory boundary always refuses until bounded traversal, sparse-map and metadata census APIs are qualified upstream. See dw06-manifest-and-inventory.txt for the design and scheduler follow-on.

The standard encryption provider, qualified sparse/no-follow/journal interfaces, actual journalled installer and maintenance integration are not implemented by this scaffold. All data verbs refuse. The supplied sizing input is about 5.47 GiB allocated, but exact archive capacity and the in-memory entry bound remain admission measurements; no on-disk inventory/sort spool is allowed. See capacity and archive-adapter for the measured-budget prerequisite and revised 6–10-day first-backup phase.
