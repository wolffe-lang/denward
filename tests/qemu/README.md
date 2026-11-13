# Storage capability observations

`observed-v1.json` records the small-store outcomes measured under QEMU on the exact image digest it names. It contains no personal files, credentials, machine identities or local paths. The 3 MiB pattern contains each byte value repeatedly, not secret data.

The assertion module checks every outcome, including expected unsupported capabilities. Its mutation self-test proves each row can reject a wrong result. Replaying the fixture is explicitly a **judge replay**, not a new QEMU run, large-file measurement, macOS receiver test or backup-tool qualification. A live runner must produce its facts from serial statuses and independent disk/receiver readback and then call the same assertions.

Observed: boot-attached USB ext2 and virtio ext3 write/readback, independently clean filesystems, outgoing shipped SSH binary roundtrip, FAT ENODEV, successful unmount but no usable newly exposed USB disk after reconnection, absent mount utility/fstab and unsupported bare sync utility. The du command returned success only on the throwaway fixture; no personal-data size is inferred.

The native macOS SSH receiver and actual encrypted stream boundary are separate future e2e rows. Do not turn this fixture into evidence for either.

The live driver requires container root, loopback-only networking, a writable KVM device, the listed binary tools and a fresh short shell-safe workspace. Run its preflight alone before scheduling a take:

```sh
python3 tools/probe-storage.py --image IMAGE --workspace WORK --preflight
python3 tools/probe-storage.py --image IMAGE --workspace WORK
```

Preflight checks prerequisites and the exact ISO digest but does not boot QEMU or claim a live result. The actual run writes serial/fact records only inside WORK, starts only private fixture processes and ends those children by pid. Source images are read-only; test disks and keys are throwaway. Missing prerequisites are failures, not silent skips.
