# Scaffold prediction

Written before the command implementation.

- CLI rows initially fail because no executable exists. Version/help become the only successful command paths.
- Every data verb returns a named unsupported outcome without source/destination/network access. A fixture tree stays byte-for-byte unchanged even when supplied paths are writable.
- Encryption is selected by default. An unavailable encrypted provider refuses before archive/store work. No fallback selects plaintext.
- Explicit plaintext without the acknowledgement fails by name; with it, backup still refuses as unimplemented.
- Arguments are never echoed in diagnostics. Independently generated secret sentinels stay out of stdout/stderr.
- Invalid/duplicate options, unknown commands, missing values and malformed digests/ids fail as usage errors. Help describes the refusal-only boundary.
- Format/store specifications declare ciphertext-only no-key verification and additional keyed authentication/archive verification. A transport receipt alone is never authenticity or restoration proof.
- Storage capability fixtures cover the observed pinned-image outcomes: USB ext2 and virtio ext3 read/write, outgoing binary SSH roundtrip, FAT ENODEV, absent mount utilities and unusable USB reconnect. Transcript judges must fail deliberate mutations. A transcript replay is not a new live QEMU take.
- The core gate is toolchain-independent. The native gate builds at the pinned compiler/stdlib and runs real CLI subprocesses. Linux native should pass locally; hosted macOS/SSH tests remain explicitly unrun until that environment executes them.
- A deliberate wrong refusal status or plaintext-default change must turn a named CLI row red. A broken transcript must turn its named judge row red. Workflow existence is not proof that GitHub ran it.
