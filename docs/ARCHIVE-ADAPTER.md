# Archive stream adapter

The public restricted-pax core is pinned at paxage revision `2c69152ba9aa760ec5104b65a23ef961bfa83368`, including its borrowed-handle writer and explicit profiles. Exact source/licence provenance and separate package glue are under `vendor/package-archive`. The internal [safe-object adapter](SAFE-OBJECT-FRAMING.md) uses this sink writer and reader without the package directory/template/output-file workflow or a plaintext spool. Its successful claim is physical framing/inventory validation only; complete BR1 backup/verify/store integration remains unfinished.

## Pinned core interface

Start with a descriptor-backed bounded sink, which can be a pipe into the encryption stage; this needs no unqualified closure/trait API. The controller owns opening, closing, lifetime, cancellation and publication. The library owns only archive framing and checked accounting.

```text
Profile { max_entries, max_data_bytes, max_extension_bytes, chunk_bytes }
writer_start(out_fd, profile) -> Writer
writer_error(writer) -> first_named_error_or_empty
writer_begin(mut writer, validated_header) -> named_error_or_empty
writer_data(mut writer, bytes) -> named_error_or_empty
writer_end(mut writer) -> named_error_or_empty
writer_finish(mut writer) -> named_error_or_empty
writer_abort(mut writer) -> named_error
inspect_with_profile(mut declared_stream, profile) -> Inventory
```

The header describes an archive member, not a source filesystem path. Begin checks canonical ordering, supported type/numeric/path/link policy, declared member length and aggregate limits before output. Data accepts bounded chunks and handles underlying short writes or fails; zero progress is an error. End checks exact member length and writes zero padding. Finish writes exactly two zero end blocks; it does not fsync, close, rename, publish a receipt or declare a backup complete. A failed writer cannot be resumed as a new archive. Existing inspect delegates to inspect-with-profile using unchanged package defaults.

The package packer retains its template/node limits, reserved-root policy, canonical owners/times, output naming and existing error behavior; only its framing helper calls are factored through the writer after byte-for-byte regression proof. Package defaults remain 100,000 entries, 16 GiB aggregate data and 1 MiB extensions. Backup requests an explicit separately qualified profile, uses only safe physical control/object members, and keeps logical home/symlink/sparse/account policy outside package extraction. Do not widen package defaults to enable a backup.

For backup, the caller precomputes immutable-source logical metadata/digests in its measured in-memory inventory, then supplies each member's header and bounded data chunks to the pipe-backed writer. Encryption consumes that pipe with backpressure and writes ciphertext to the store. Whole-file plaintext buffers, plaintext archive files, plaintext manifest sidecars and inventory/sort spools are forbidden. A bounded byte-sink variant can be added only if its Wolf callback surface is separately qualified; it is not a prerequisite for this descriptor form.

The release entry bound is the measured combined inventory footprint plus runtime/encryption/reader overhead inside 256 MiB, not the former million-entry proposal. Before enabling data operations, measure bytes per entry across representative and worst-case names/maps, publish a safe numerical ceiling and make inspect report/refuse above it. Until then the inventory budget is unqualified and no successful backup is advertised.

## Qualification boundaries

The pinned core's package regression and framing rows precede this integration. The safe-object adapter adds its own independent-byte, name/type/normalization, digest, borrowed-handle and failure rows. The remaining whole-backup pipeline obligations are listed separately below; their presence is not a claim that encryption or large-stream qualification has run.

- Existing package output is byte-identical before/after factoring; all package malformed-input and boundary gates remain unchanged.
- Controller-owned fd remains open after success/failure; the writer never creates, closes, syncs or publishes files on its own.
- Pipe-backed one-byte/short reads/writes, backpressure, consumer failure, EINTR/zero-progress and producer cancellation propagate by name without a successful finish.
- Begin/data/end ordering and wrong declared lengths, integer overflow, duplicate/conflicting paths, nonzero padding and trailing bytes fail independently.
- Explicit profile boundaries reject one past entries/data/extensions/chunk limits; default package limits do not change. New backup profiles cross 16 GiB in generated-stream tests, not by silently weakening the old reader.
- Existing GNU tar/bsdtar black-box contrasts and independent bytes/metadata checks cover normal and hostile headers. No new parser implementation is introduced.
- The archive→encryption→store spy sees no plaintext at the final sink; a deliberate pass-through fallback and ignored short write fail named rows.
- Input growth at 1 GiB, 8 GiB and 32 GiB stays within fixed buffers/RSS. Large rows use bounded Linux jobs and no huge tracked fixtures; streaming hash-sink proof is separate from real-store durability.

## Revised work budget

Allow 6–10 focused lane-days for the first backup/verify and primary-store integration phase: 2–3 for the upstream sink/profile extension and unchanged-default regression, 3–5 for backup inventory/archive/verify integration, and 1–2 for combined stream/bounds/large-input qualification. The Mac-first SSH endpoint develops alongside that work rather than waiting for restore. Encryption qualification/review and the measured in-memory entry ceiling remain independent release prerequisites. Host queues and upstream defects are additional time.

The upstream archive-only change is complete and its exact pin is imported. No active encryption branch is incorporated by this checkpoint. No CLI success, inventory capacity, encrypted primary store or whole-backup qualification is inferred from the framing API.
