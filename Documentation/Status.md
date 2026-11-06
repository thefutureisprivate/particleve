# Implementation and validation status

The native ParticleOS fork, installer, storage/update coordination and host
configuration are implemented in source. This is an uncommissioned candidate;
unit tests and package builds do not establish boot or hardware acceptance.
The original PLAN.md milestones remain open until their complete exit criteria
have evidence.

| Area | Current evidence | Still required |
| --- | --- | --- |
| Source/configuration | Full upstream Git history and signed implementation published; Fedora 45 native profile; runtime/initrd/tools stable-systemd inputs; resolved summary checks pass; all four source-change webhooks verified against commit fd52ed9 | Complete image validation |
| OBS | Old project deleted before uploads; new project and persistent signing key; all RPM builds passed; image 21.1 published and accepted by the client with all six artifacts, GPG index, EFI signatures and UKI checks | Dependency-only rebuild evidence and boot acceptance |
| Host integration | Verified 21.1 plan applied to two disposable 80 GiB disks through partitioning, per-device LUKS, Btrfs RAID1, md/LUKS swap and root creation; fixed tmpfiles/read-only SSH and image-policy labeling issues reproduced and probed under SELinux enforcing | Complete fresh installation with fixes, cold-home SSH, actual initrd/TPM/verity boot, both degraded boot paths and replacement |
| Update maintenance | Durable lock/version/state, two-disk hash verification, boot counters/quarantine, Berlin window, bounded ACPI shutdown and abort restoration | Real sysupdate/ESP interruptions, boot failure/watchdog/fallback, external startup policy and retained-state compatibility |
| Local checks | Ruff and shell syntax; 50 tests including actual disposable GPG signatures, temporary ESP counter/capsule preservation, actual dirty-file signature-slot overwrite, interrupted transactions and VM refusal/late exit/recovery | Unit tests do not exercise actual QEMU, firmware, TPM, SELinux or block devices |
| Firmware | Signed helper package and metadata-only refresh integration; persistent manual-maintenance exclusion | Device discovery/ESP selection and supervised real update, or evidence no eligible update exists |
| Commissioning | Evidence-bound command; all automatic OS timers disabled by default | Full acceptance matrix, Intel/AMD and controller/NIC variation, measured memory/capacity minima, unattended update and no-update window |

The disposable Fedora recovery VM booted with Secure Boot, nested KVM and SSH.
Preflight rejected its Fedora libtpms 0.10.2 software TPM because it cannot load
the project's RSA4096 authorization key. The same VM passed all preflight checks
with a test-only upstream libtpms build at commit
`5b7bb9b8da269440dcba3f2f7f4bc40197d3c9e7`, profile `default-v2`, and loaded the
actual project public key successfully. Production image packages are unchanged.
The two disposable disks have now been partitioned; installation stopped safely
at root initialization before boot entries were provisioned. This is recovery and
installer-component evidence, not a ParticleVE boot/TPM acceptance result.

The generic UKI currently uses tty0. A configured serial getty can supply a login
console, but kernel/initrd messages for arbitrary serial ports have not been
validated. No supported hardware list or measured minimum RAM is published yet.
No physical installation disks or firmware have been modified by implementation.
No persistent-data migration has been added or approved.
