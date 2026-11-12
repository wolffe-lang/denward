# Compatibility v1

The archive, logical manifest, store receipt, CLI claim labels and restore journal have separate explicit versions. The standard encrypted envelope has its own published format/version; denward must not silently redefine it. An encrypted file produced by denward must interoperate with the qualified reference tool, and vice versa, before use with real data.

The scaffold refuses every data operation. It emits no backup fixture labelled recoverable, accepts no real archive as valid and has no successful ciphertext verify path. Text fixtures are parser/judge examples only. No generated empty archive or placeholder encrypted header may become a de facto v1 backup.

Once a backup version ships, retain a frozen fixture produced by that old binary. A newer tool must verify/restore it with independent expected logical state. Unknown schema, feature, encryption profile, record fields or required metadata fails by name before target writes. Do not regenerate old fixtures to hide incompatibility. A migration is an explicit verified conversion to a new backup, retaining the original until independent roundtrip proof.

Default encryption is a policy boundary from the first CLI scaffold. Explicit plaintext plus held-media acknowledgement stays an exceptional, visibly labelled mode. Missing encrypted-provider support, unsupported entropy or a wrong key must never select plaintext. A no-key stored-byte integrity verdict must not be named authenticated, decryptable, restorable or complete restoration.

Package-specific archive caps and staging rules are not backup compatibility guarantees. Reuse requires exact public provenance and a bounded stream adapter with independent tests. No upstream code is currently imported, and no unpublished source identity is tracked here.
