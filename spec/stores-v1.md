# Stores v1

## Primary: macOS SSH receiver

The first endpoint runs natively on macOS arm64 under an ordinary dedicated account through macOS's OpenSSH server. The same endpoint builds/runs on Linux. It needs no PAX SSH server, network daemon of its own or root privilege. The destination is a private directory on the Mac's encrypted volume, mode 0700, with objects/receipts mode 0600. The owner confirms the volume's encrypted-at-rest status during setup; directory permissions or a successful write are not encryption proof. Tests use a throwaway encrypted-volume-status fixture and private SSH service, never a real personal directory.

A trusted alias binds SSH destination/user/port, strict host-key pin, key reference, absolute endpoint executable and fixed destination directory. The client starts `ssh -T` through an argv vector, drains raw stdout/stderr and checks the command's exit status. The remote shell receives only a fixed endpoint invocation plus validated ASCII ID/digest/length values. No user-controlled command or unquoted path is concatenated into shell syntax. Never send a passphrase/password/key's contents in argv or environment dumps.

## Receive and publish

1. `receive --directory DIR --id ID` takes an exclusive lock for that ID and creates a fresh private partial object, refusing existing complete IDs and unsafe destination/ancestor types. It consumes raw stored bytes to EOF with checked bounds. For encrypted selection these bytes are ciphertext, not an archive stream that the receiver decrypts.
2. Write and sync the partial file, sync all created parent directories, independently read/hash its complete bytes, then persist received state. Emit exactly one bounded UTF-8 JSON receipt line on stdout and status 0. Failure produces no successful receipt and no complete object. Stderr contains only safe diagnostics. This state is **received**, not published or trusted.
3. The sender compares that receipt with its own post-encryption digest/length and the SSH command status. Only on agreement does it run `receive --directory DIR --id ID --commit --expect-sha256 HEX --expect-bytes N` through another fixed invocation.
4. Commit revalidates held regular-file identity, length/digest and received state, then durably publishes the immutable object and receipt with final complete state last. Sync files and all affected directories. No mutable replace of an existing complete ID; duplicate same-ID input is a conflict unless an explicitly idempotent exact match is proved. A cut at any step yields either incomplete received state or a fully verifiable complete object.

The external receipt is one strict JSON object with fields in canonical order: `schema` = 1, `id`, `state` (`received` or `complete`), `format` (`encrypted` or `plaintext`), `length` (nonnegative checked integer), `sha256` (64 lowercase hex). It ends with LF, is at most 4096 bytes, rejects duplicate/unknown fields and never contains plaintext digests, source paths, account contents, key material or passphrases. The selected format is carried by trusted operation setup; the receiver must not guess from a coincidental byte prefix. Until a concrete authenticated provider exists, an encrypted operation cannot be started by the producer.

The archive ID is a validated opaque ASCII identifier, not a relative path. Descriptor-relative no-follow path walking confines writes to the configured destination. Do not use a string-prefix check as confinement. Received records, partial bytes and final receipts never follow uploaded symlinks. Permission/ownership, wrong-device/volume, ENOSPC/EIO, short writes, readback mismatch and disconnects fail before complete publication.

`send --receipt` returns the complete receipt only. `send` returns raw complete object bytes and status; it never streams an uncommitted partial object. A restore first caches the entire SSH object privately and verifies its independently expected stored-byte digest before parsing/decrypting/applying. Receiver readback plus SSH encryption does not replace client-side verification or independent receipt retention.

No transfer resume in v1: restart a failed upload/download from byte zero. Restore's transaction replay is a different capability. Partial cleanup is explicit and must not remove complete or in-use objects. No secure flash-erasure promise is made.

## Second copy: separate disk

Write an ordinary complete stored-byte object and receipt to another physical disk. Identify the disk/partition by stable identity, not a remembered device letter; refuse the reinstall target as a backup store. Use qualified ext3, or an explicitly warned compatible ext2 route. Connect USB storage before boot: the measured client image did not expose a usable new disk after reconnect. FAT has no evidenced general writable mount. A second file on the same disk/volume is not an independent second copy.

Local stores use the same bounded sink/finalization/receipt semantics and full readback checks as SSH. They never silently switch an encrypted operation to plaintext. Plaintext anywhere requires explicit selection, held media and acknowledgement. Unheld/offsite destinations remain disabled until the standard encrypted format and its key-recovery proof are qualified.

## Capacity and proof

No personal-data size has been supplied. Inventory must report logical/stored bytes, padding/control costs, maximum object and inode counts. Reserve a complete new archive, a retained complete previous archive and `max(10% of archive size, 1 GiB)` headroom, plus actual filesystem metadata/inodes. Restore separately reserves complete SSH cache, restored/staged data and preimages. Do not equate allocated-space du output with sparse logical/archive size.

Native macOS endpoint e2e, Linux endpoint e2e and the PAX shipped-client-to-macOS-sshd path are required before primary-store readiness. Test short writes/backpressure, EOF/status, changed host key, disconnect, disk full, receipt corruption, commit cuts, strict file modes and no plaintext sentinels at the encrypted store boundary. A Linux private OpenSSH fixture demonstrates only that route, not macOS execution.
