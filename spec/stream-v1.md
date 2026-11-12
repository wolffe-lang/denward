# Stream v1

## Pipeline

`inventory → archive source → encryption stage → stored-byte sink`

Archive and encryption stages do not choose filesystems, filenames, SSH commands or retention. Stores do not parse archives, hold decryption keys or receive plaintext when encrypted format is selected. A source is a bounded byte producer; a sink accepts bounded byte chunks, applies backpressure and reports errors without truncation. No stage may buffer the entire archive or retain one allocation per input chunk.

The adapter contract, expressed independently of Wolf's eventual module layout:

```text
Source.read(max_bytes) -> bytes | eof | named_error
Sink.write(bytes) -> accepted_count | named_error
Sink.finish() -> received_receipt | named_error
Sink.abort() -> named_error_or_ok
Encryption.open(context, downstream_sink) -> plaintext_sink | named_error
Encryption.finish() -> authenticated_end_written | named_error
```

`max_bytes` is positive and at most 131072. A write may be short; its caller advances exactly by the accepted count and retries the remainder. A zero-byte write with nonempty input is an error, never a busy loop. All byte counts are checked before increment. EOF is distinct from an I/O error. The encryption provider chooses its own standard chunk size within the caller's bound. Source and downstream errors propagate to the controller, abort the operation and leave no complete marker. Cancellation has the same rule.

The controller owns success. It computes the plaintext archive SHA-256 in memory before encryption and the complete ciphertext SHA-256 after encryption. It compares the latter and exact byte length to the receiver's independent readback receipt before publication. No plaintext digest is persisted in a public receipt, log or sidecar. There is no circular hash embedded in the archive.

Encryption is the default format selection. `Encryption.open` refuses `encrypted-format-provider` until the standard-format provider is available, keys/randomness requirements are met and its independently reviewed gates pass. This happens before opening a plaintext-output file or starting a receive session. No exception handler substitutes a pass-through stream. The only pass-through mode is an explicitly selected `--plaintext --ack-plaintext-owner-held` operation on held local media, never SSH. The primary-store path always receives ordinary age v1 ciphertext.

## Verification

Without a key, `verify` reads every stored byte and checks the externally expected ciphertext length/SHA-256. It may validate a bounded receipt's syntax and format identifier but does not claim recipient/header authentication, decryption, archive validity or recoverability. A digest obtained only from the same untrusted store is not independent authenticity.

With a key, verification additionally authenticates the standard envelope/header and every chunk through its final authenticated end marker, computes the plaintext archive digest and validates complete physical/logical archive inventories and per-file digests. No unauthenticated chunk is exposed. No restored target byte is written until the whole backup's authentication and integrity pass. No plaintext archive/cache/manifest or inventory spool is allowed. Cache ciphertext only; use a second authenticated decrypt pass for apply after full preflight. First-release inventory is wholly in memory at a separately measured entry bound, or refuses `inventory_budget_unqualified`.

The provider must distinguish wrong-key/authentication/truncation/unsupported-format errors by documented safe reason names without leaking keys, passphrases, salts or secret file contents. The exact wire format, recipient types, key input and randomness capability are owned by the encrypted-format specification. This interface deliberately does not mint an envelope header, cipher, KDF, nonce schedule or new cryptographic framing.

## Tests before implementation is enabled

Use a producer/sink harness with one-byte and short reads/writes, backpressure, EOF versus failure, cancellation and finalization errors. Independently hash bytes crossing each boundary. With encrypted selection, prove the store never sees plaintext sentinels. Plant a pass-through fallback and an ignored short write; each must fail by name. No-key and keyed verify must have distinct successful claim labels. The refusal-only scaffold has neither successful verification path.
