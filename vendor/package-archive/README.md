# Shared archive dependency

The exact source/licence closure comes from public [paxage](https://github.com/wolffe-lang/paxage) revision `2c69152ba9aa760ec5104b65a23ef961bfa83368`. `provenance.json` records every upstream path, Git blob and SHA-256. Source files are byte-identical to that revision. The six `wolf.pkg` descriptors are separate local import glue with their own recorded hashes. `tools/check-archive-pin.py` checks identity, closure, source/licence bytes and glue before compilation.

The closure contains packing, payload, literal, schema, model and version. The borrowed-handle writer and explicit reader profile are reused; package CLI, staging, transactions and extraction are not backup authority. Upstream package defaults remain unchanged. The closure is compiled with denward's own unchanged toolchain/std pins.

The safe-member adapter keeps logical restore metadata outside physical archive paths. It does not enable CLI data operations, encryption, a production inventory capacity or store publication. Metadata remains in memory and belongs to the future measured combined inventory budget; no inventory/sort spill is enabled. See [the adapter contract](../../docs/SAFE-OBJECT-FRAMING.md).

Both upstream licence files are included verbatim. No foreign archive implementation source is used.
