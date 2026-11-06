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
| Host integration | 22.1 installed completely on fresh disposable 80 GiB disks, including both ESPs and firmware entries; actual Btrfs RAID1 and synchronized md/LUKS swap; target-policy labeling succeeded with SELinux enforcing | First normal boot found modules removed by incorrect mkosi glob syntax; corrected selectors and final artifact driver gate need boot validation, followed by cold-home SSH, TPM, degraded boots and replacement |
| Update maintenance | Durable lock/version/state, two-disk hash verification, boot counters/quarantine, Berlin window, bounded ACPI shutdown and abort restoration | Real sysupdate/ESP interruptions, boot failure/watchdog/fallback, external startup policy and retained-state compatibility |
| Local checks | Ruff and shell syntax; 52 tests including actual disposable GPG signatures, dirty-file signature-slot overwrite, final driver retention, interrupted transactions and VM failure recovery; pinned mkosi's actual matcher reproduces and verifies the selector fix | Unit tests do not replace normal-boot and hardware acceptance |
| Firmware | Signed helper package and metadata-only refresh integration; persistent manual-maintenance exclusion | Device discovery/ESP selection and supervised real update, or evidence no eligible update exists |
| Commissioning | Evidence-bound command; all automatic OS timers disabled by default | Full acceptance matrix, Intel/AMD and controller/NIC variation, measured memory/capacity minima, unattended update and no-update window |

The disposable Fedora recovery VM booted with Secure Boot, nested KVM and SSH.
Preflight rejected its Fedora libtpms 0.10.2 software TPM because it cannot load
the project's RSA4096 authorization key. The same VM passed all preflight checks
with a test-only upstream libtpms build at commit
`5b7bb9b8da269440dcba3f2f7f4bc40197d3c9e7`, profile `default-v2`, and loaded the
actual project public key successfully. Production image packages are unchanged.
The corrected 22.1 installer completed on a fresh virtual pair. Its first normal
boot reached the storage prompt but failed verity activation because the old
regex-style module selector retained no kernel modules. Runtime selection now
uses mkosi's glob syntax and directory selectors end in `/`; final EROFS checks
require the boot, storage and Intel/AMD KVM drivers after module filtering.
Successful normal boot and unattended TPM unlock remain unvalidated.
The failed initrd also exposed a gap before the normal boot watchdog. A separate
five-minute initrd deadline now stops at switch-root and retries failed boots;
actual timeout/counter/fallback behavior still requires acceptance testing.

The generic UKI currently uses tty0. A configured serial getty can supply a login
console, but kernel/initrd messages for arbitrary serial ports have not been
validated. No supported hardware list or measured minimum RAM is published yet.
No physical installation disks or firmware have been modified by implementation.
No persistent-data migration has been added or approved.
