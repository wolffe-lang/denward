# Backup v1

## Domains

The logical recovery set is not the base system. Homes include dotfiles, repositories/uncommitted work, backups, games/saves and media. Root's home may be `/`; classify its personal top-level paths against the image manifest rather than recursively archiving the whole root. Include semantic account/group/password records, image-manifest-derived added/changed/deleted configuration, persistent non-cache application data, selected local programs/data, restricted audit history and installed-beyond-image inventory. Missing baselines, unclassified persistent data and unknown ownership are named blockers. Preserve old SSH host identity while keeping the new installation's boot/disk invariants.

Exclude the old kernel/base image/ESP/partition table, pseudo-filesystems, runtime process/lock/pid state, sudo authentication timestamps, leases/generated resolver state, known disposable caches and backup/staging destinations. Do not exclude arbitrary home directories merely because they are called cache/build/target. A package list does not recover personal data or prove an unmanaged executable is a package.

## Archive profile

The plaintext archive is uncompressed restricted POSIX pax: 512-byte ustar headers, per-entry pax extensions only when necessary, canonical ordering/numeric representation, zero padding and exactly two zero end blocks. Global pax/GNU headers, unknown required extensions, archive device/socket/FIFO entries, set-ID headers and physical sparse extensions are forbidden. Archive entries are ordinary directories and regular data objects only; no archive link can alter extraction traversal.

Contents:

- `control/manifest`: versioned logical file records, source/baseline identities, selection and exclusions.
- `control/accounts`: restricted original account databases as opaque payload, not diagnostic text.
- `control/config-defaults/`: necessary original configuration baseline objects, matching the old image inventory; comparison data only.
- `control/installed`: package/unmanaged provenance and compatibility report.
- `objects/`: bounded regular content objects. The manifest distinguishes content equality from hard-link identity. Sparse maps reference ordered extent bytes. Symlink text is data, not an archive symlink.

Logical file digests hash complete logical content, including zero-filled holes. Object digests hash exact stored object bytes. The plaintext archive digest covers every archive byte. None is a self-referential embedded archive hash. Physical object metadata is normalized; original ownership, full modes and restorable times live in logical records. Times unsupported by setters are explicitly observed-only. Unknown metadata and unavailable sparse-map enumeration refuse by name rather than flattening silently.

Limits: 128 KiB maximum I/O request, 256 MiB process RSS with metadata spilled privately, 4096-byte paths/link texts, 1,048,576 logical entries and 1,048,576 extents per file. All lengths use checked signed-64-bit accounting and explicit source/store/output bounds; allocation precedes neither bounds nor validation. Exceeding a bound is a refusal, never truncation. These backup limits require independent qualification; an upstream package-specific smaller cap is not silently treated as the backup policy.

## Encryption boundary

Archive output feeds the standard encryption stream provider before it reaches a store. Default selection is encrypted; a missing provider refuses. Its envelope identifier, recipient grammar and wire format are specified independently from a published standard and are not invented or frozen here. Plaintext is an explicit held-media exception, never an implicit fallback.

For encrypted backups, the store receives ciphertext only, including any provider framing. The plaintext archive digest stays inside the encrypted authority/control domain or a restricted local operation record, not a public receipt. The external receipt binds complete stored ciphertext byte length and SHA-256. Plaintext receipts identify the explicit plaintext mode without mislabelling its bytes ciphertext.

Verification has two different claims: no-key stored-byte integrity versus keyed authenticated-envelope and full logical archive verification. Neither an unkeyed digest nor SSH transport makes a coherently replaced backup authentic. Keep an independently held expected stored-byte digest. The full input must verify before target restoration; no stream is applied while its terminal integrity/authentication is unknown.

The archive reader/packer will reuse an approved owned restricted-pax core at an exact public pin after its stream/bounds adapter is qualified. No implementation is vendored in the scaffold. Safe-object names avoid broadening package path policy or allowing home paths as extraction authority.
