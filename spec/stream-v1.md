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

The controller owns success. It computes the plaintext archive SHA-256 before encryption and the complete stored-byte SHA-256 after encryption. It compares the latter and exact byte length to the receiver's independent readback receipt before requesting publication. The plaintext digest is returned only to the restricted operation controller/audit state, not a public ciphertext receipt. There is no circular hash embedded in the archive.

Encryption is the default format selection. `Encryption.open` refuses `encrypted-format-provider` until the standard-format provider is available, keys/randomness requirements are met and its independently reviewed gates pass. This happens before opening a plaintext-output file or starting a receive session. No exception handler substitutes a pass-through stream. The only pass-through mode is an explicitly selected `plaintext` operation with the held-media acknowledgement; the receipt says plaintext.

## Verification

Without a key, `verify` reads every stored byte and checks the externally expected ciphertext length/SHA-256. It may validate a bounded receipt's syntax and format identifier but does not claim recipient/header authentication, decryption, archive validity or recoverability. A digest obtained only from the same untrusted store is not independent authenticity.

With a key, verification additionally authenticates the standard envelope/header and every chunk through its final authenticated end marker, computes the plaintext archive digest and validates complete physical/logical archive inventories and per-file digests. No unauthenticated chunk is exposed. No restored target byte is written until the whole backup's authentication and integrity pass. A private staging/cache stream may contain authenticated plaintext only under the explicit local media policy and must never be confused with a completed restoration.

The provider must distinguish wrong-key/authentication/truncation/unsupported-format errors by documented safe reason names without leaking keys, passphrases, salts or secret file contents. The exact wire format, recipient types, key input and randomness capability are owned by the encrypted-format specification. This interface deliberately does not mint an envelope header, cipher, KDF, nonce schedule or new cryptographic framing.

## Tests before implementation is enabled

Use a producer/sink harness with one-byte and short reads/writes, backpressure, EOF versus failure, cancellation and finalization errors. Independently hash bytes crossing each boundary. With encrypted selection, prove the store never sees plaintext sentinels. Plant a pass-through fallback and an ignored short write; each must fail by name. No-key and keyed verify must have distinct successful claim labels. The refusal-only scaffold has neither successful verification path.
