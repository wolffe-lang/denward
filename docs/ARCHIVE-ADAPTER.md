# Archive stream adapter

The shared restricted-pax component needs a small upstream extension before backup reuse. Its existing package packer owns a directory/template/output-file workflow and is not a ready encryption-stream producer. Do not route that packer through a plaintext archive spool. Extend the shared component, retain its package defaults and tests, then import an exact reviewed public pin. No upstream implementation or private source identity is copied here yet.

## Proposed interface

Start with a descriptor-backed bounded sink, which can be a pipe into the encryption stage; this needs no unqualified closure/trait API. The controller owns opening, closing, lifetime, cancellation and publication. The library owns only archive framing and checked accounting.

```text
Limits { max_entries, max_data_bytes, max_extension_bytes, max_chunk_bytes }
writer_start(out_fd, limits) -> Writer | named_error
writer_begin(mut writer, validated_header) -> ok | named_error
writer_data(mut writer, bytes) -> ok | named_error
writer_end(mut writer) -> entry_result | named_error
writer_finish(mut writer) -> framing_complete | named_error
inspect_with_limits(mut declared_stream, limits) -> Inventory | named_error
```

The header describes an archive member, not a source filesystem path. Begin checks canonical ordering, supported type/numeric/path/link policy, declared member length and aggregate limits before output. Data accepts bounded chunks and handles underlying short writes or fails; zero progress is an error. End checks exact member length and writes zero padding. Finish writes exactly two zero end blocks; it does not fsync, close, rename, publish a receipt or declare a backup complete. A failed writer cannot be resumed as a new archive. Existing inspect can delegate to inspect-with-limits using unchanged package defaults.

The package packer retains its template/node limits, reserved-root policy, canonical owners/times, output naming and existing error behavior; only its framing helper calls are factored through the writer after byte-for-byte regression proof. Package defaults remain 100,000 entries, 16 GiB aggregate data and 1 MiB extensions. Backup requests an explicit separately qualified profile, uses only safe physical control/object members, and keeps logical home/symlink/sparse/account policy outside package extraction. Do not widen package defaults to enable a backup.

For backup, the caller precomputes immutable-source logical metadata/digests in its measured in-memory inventory, then supplies each member's header and bounded data chunks to the pipe-backed writer. Encryption consumes that pipe with backpressure and writes ciphertext to the store. Whole-file plaintext buffers, plaintext archive files, plaintext manifest sidecars and inventory/sort spools are forbidden. A bounded byte-sink variant can be added only if its Wolf callback surface is separately qualified; it is not a prerequisite for this descriptor form.

The release entry bound is the measured combined inventory footprint plus runtime/encryption/reader overhead inside 256 MiB, not the former million-entry proposal. Before enabling data operations, measure bytes per entry across representative and worst-case names/maps, publish a safe numerical ceiling and make inspect report/refuse above it. Until then the inventory budget is unqualified and no successful backup is advertised.

## Rows before the upstream change

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

The upstream change waits for publication confirmation, uses its own archive-only branch/PR and does not modify another active branch. This design does not authorize that change before confirmation.
