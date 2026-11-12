# Shared archive dependency

No source is vendored here yet. The approved owned restricted-pax implementation has been audited privately while its publication is pending. Its identity and revision are intentionally not copied into this public tree before confirmation.

The audit found a sequential descriptor reader with exact declared-length framing and bounded data buffers, but an in-memory sorted inventory and package-specific limits. The packer owns output-file creation and package-manifest rendering; it is not a ready byte-sink archive writer. Its partial-output behavior must not be mistaken for the backup completion protocol.

Before importing anything, record exact public source/licence provenance, isolate or parameterize the bounded writer/reader interfaces, preserve existing package defaults and tests, and independently qualify the backup limits, metadata spill and encryption sink boundary. Do not duplicate a parser or widen package extraction policy to accept logical home paths. Safe physical object paths and logical restore policy are separate layers.

The command scaffold imports none of this component and refuses all data operations.
