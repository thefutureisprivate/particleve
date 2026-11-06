# Implementation and validation status

The native ParticleOS fork, installer, storage/update coordination and host
configuration are implemented in source. This is an uncommissioned candidate;
unit tests and package builds do not establish boot or hardware acceptance.
The original PLAN.md milestones remain open until their complete exit criteria
have evidence.

| Area | Current evidence | Still required |
| --- | --- | --- |
| Source/configuration | Full upstream Git history and signed implementation published; Fedora 45 native profile; runtime/initrd/tools stable-systemd inputs; resolved summary checks pass | Publish the remaining build fixes; register source-change webhooks |
| OBS | Old ParticleOS project deleted before uploads; new owned project and persistent signing key created; separately PE-signed fwupd helper build passed | Integration and pinned mkosi builds passed; complete native image signing/publication, dependency/source rebuild evidence |
| Host integration | Geometry/stable identity validation, Btrfs RAID1 over per-device LUKS2, md/LUKS swap, independent ESPs, homed/userdb SSH, networkd/nftables, vmspawn template integration | Disposable-disk installation, cold-home SSH, actual initrd/TPM/verity boot, both degraded boot paths and replacement |
| Update maintenance | Durable lock/version/state, two-disk hash verification, boot counters/quarantine, Berlin window, bounded ACPI shutdown and abort restoration | Real sysupdate/ESP interruptions, boot failure/watchdog/fallback, external startup policy and retained-state compatibility |
| Local checks | Ruff and shell syntax; 42 tests including actual disposable GPG signatures, temporary ESP counter/capsule preservation, interrupted transactions and VM refusal/late exit/recovery | Unit tests do not exercise actual QEMU, firmware, TPM, SELinux or block devices |
| Firmware | Signed helper package and metadata-only refresh integration; persistent manual-maintenance exclusion | Device discovery/ESP selection and supervised real update, or evidence no eligible update exists |
| Commissioning | Evidence-bound command; all automatic OS timers disabled by default | Full acceptance matrix, Intel/AMD and controller/NIC variation, measured memory/capacity minima, unattended update and no-update window |

The generic UKI currently uses tty0. A configured serial getty can supply a login
console, but kernel/initrd messages for arbitrary serial ports have not been
validated. No supported hardware list or measured minimum RAM is published yet.
No physical installation disks or firmware have been modified by implementation.
No persistent-data migration has been added or approved.
