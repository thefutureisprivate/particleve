# Implementation and validation status

The native ParticleOS fork, installer, storage/update coordination and host
configuration are implemented in source. This is an uncommissioned candidate;
unit tests and package builds do not establish boot or hardware acceptance.
The original PLAN.md milestones remain open until their complete exit criteria
have evidence.

| Area | Current evidence | Still required |
| --- | --- | --- |
| Source/configuration | Full upstream Git history published; Fedora 45 native profile; runtime/initrd/tools stable-systemd inputs; resolved summary checks pass; all four source-change webhooks exercised | Complete image validation |
| OBS | Old project deleted before uploads; new project and persistent signing key; all RPM builds passed; 26.1 and 26.2 accepted from the public feed with all six artifacts, GPG index, EFI signatures and UKI checks; rebuilding only the integration RPM produced 26.2 with unchanged Git sources and persistent-state versions | Boot acceptance |
| Host integration | 26.1 installed completely on disposable 80 GiB disks, both ESPs/firmware entries, Btrfs RAID1 and synchronized md/LUKS swap; a marked unselected disk remained byte-for-byte unchanged; signed normal boot activated verity and unlocked both state members | Exact-UUID swap assembly fix needs normal-boot validation, followed by cold-home SSH, TPM, degraded boots and replacement |
| Update maintenance | Durable lock/version/state, two-disk hash verification, boot counters/quarantine, Berlin window, bounded ACPI shutdown and abort restoration | Real sysupdate/ESP interruptions, boot failure/watchdog/fallback, external startup policy and retained-state compatibility |
| Local checks | Ruff and shell syntax; 52 tests including actual disposable GPG signatures, dirty-file signature-slot overwrite, final driver retention, interrupted transactions and VM failure recovery; pinned mkosi's actual matcher reproduces and verifies the selector fix | Unit tests do not replace normal-boot and hardware acceptance |
| Firmware | Signed helper package and metadata-only refresh integration; persistent manual-maintenance exclusion | Device discovery/ESP selection and supervised real update, or evidence no eligible update exists |
| Commissioning | Evidence-bound command; all automatic OS timers disabled by default | Full acceptance matrix, Intel/AMD and controller/NIC variation, measured memory/capacity minima, unattended update and no-update window |

The disposable Fedora recovery VM booted with Secure Boot, nested KVM and SSH.
Preflight rejected its Fedora libtpms 0.10.2 software TPM because it cannot load
the project's RSA4096 authorization key. The same VM passed all preflight checks
with a test-only upstream libtpms build at commit
`5b7bb9b8da269440dcba3f2f7f4bc40197d3c9e7`, using a custom profile derived from
`default-v2` with host-disabled algorithms removed, and loaded the actual project
public key successfully. Production image packages are unchanged.

The 26.1 image contains 4,850 kernel modules; its signed normal boot activated
verity and unlocked both encrypted state members. The initrd then failed because
mdadm rejects a name-only array definition. Recovery reproduced that rejection;
assembly with the recorded UUID and explicit swap partition identities passed,
including single-member startup and restoration to synchronized two-member RAID1.
The corrected initrd uses that exact-identity path. Successful switch-root and
unattended TPM unlock remain unvalidated.

The separate initrd watchdog now uses systemd's initrd presets and survives
emergency isolation. A real isolation test with the exact revised units, a
ten-second deadline and poweroff override executed its evidence marker and stopped
the disposable recovery VM without QMP intervention. Cancellation at switch-root
and actual five-minute timeout/counter/fallback behavior still require acceptance.
Negative preflight reported wrong serial and insufficient RAM without changing
either target's partition-header regions. The real client rejected a one-byte
tampered EFI helper without any disk write.

The generic UKI currently uses tty0. A configured serial getty can supply a login
console, but kernel/initrd messages for arbitrary serial ports have not been
validated. No supported hardware list or measured minimum RAM is published yet.
No physical installation disks or firmware have been modified by implementation.
No persistent-data migration has been added or approved.
