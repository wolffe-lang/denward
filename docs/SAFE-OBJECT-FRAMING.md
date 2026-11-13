# Safe object framing

This is the physical archive sublayer of BR1. It is an internal API, not an enabled backup or restore operation. CLI data verbs still refuse. A complete backup additionally needs the logical manifest/control parsers, qualified source inventory, measured admission ceiling, reviewed encryption/controller and store completion protocol.

## Dependency

The source closure is pinned to public paxage revision `2c69152ba9aa760ec5104b65a23ef961bfa83368`. A provenance manifest binds exact source and licence bytes. Added package descriptors are local import glue, not modified upstream implementation. The closure is compiled against denward's unchanged toolchain/std pins. Package-specific CLI, staging and extraction are not imported as backup authority.

## Interface

`archive.start(handle, profile)` returns a writer borrowing the runtime output handle. The trusted caller supplies explicit resource limits; this is not a qualified production backup profile. `directory(mut writer, path)` admits only `control` and `objects`. `file(mut writer, Member { path, length, sha256 }, mut declared_source)` incrementally hashes and copies exactly one declared source window. `finish` requires both directories and all four controls before the pinned writer's exact end marker. `abort` and `error` expose latched safe reason names. No source/output handle is opened, closed, duplicated, sought, synced or published by this layer.

Regular paths are exactly `control/accounts`, `control/config-defaults`, `control/installed`, `control/manifest`, or `objects/` followed by a lowercase SHA-256. Object names bind their exact data digest. All regular members are mode 0600, directories 0700, owners zero and writer timestamps zero. Logical names, original modes/owners/times, hard-link groups, symlink text and sparse maps are not physical extraction authority. Physical links and arbitrary extra members are rejected.

`archive.inspect(mut declared_stream, profile)` reuses the pinned reader to hash every physical member and then checks the complete safe-member inventory, normalization and object-name digests. Its successful claim is physical archive validation only: it does not parse logical JSON, authenticate an encrypted envelope or establish recoverability. Existing reader numeric/framing rules remain unchanged; no claim of byte-canonical acceptance is added.

## Controller responsibilities

Sources must remain stable, bounded and correctly positioned. Distinct runtime handles must not alias mutable source/output storage. A source error or digest mismatch aborts the archive without final blocks. Failure may follow a partial write; discard the session and never publish it. The controller separately hashes the complete archive before encryption, propagates all producer/encryption/store statuses and owns completion. This layer never substitutes plaintext for an unavailable encryption provider and never spools plaintext or inventory to disk.

The physical inventory retained by the core belongs to the eventual measured combined memory budget. A test-supplied profile does not enable a nonzero release inventory capacity. Large-stream tests are capped Linux-only; they are not real-store durability or logical restoration tests.
