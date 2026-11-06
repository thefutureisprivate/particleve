# Implementation and validation status

The native ParticleOS fork, installer, storage/update coordination and host
configuration are implemented in source. This is an uncommissioned candidate;
unit tests and package builds do not establish boot or hardware acceptance.
The original PLAN.md milestones remain open until their complete exit criteria
have evidence.

| Area | Current evidence | Still required |
| --- | --- | --- |
| Source/configuration | Full upstream Git history published; Fedora 45 native profile; runtime/initrd/tools stable-systemd inputs; resolved summary checks pass; all four source-change webhooks exercised | Complete image validation |
| OBS | Old project deleted before uploads; new project and persistent signing key; all RPM builds passed; 28.1 accepted from the public feed with all six artifacts, GPG index, EFI signatures and UKI checks; rebuilding only the integration RPM produced 26.2 from 26.1 with unchanged Git sources and persistent-state versions | Boot acceptance of the revised runtime configuration |
| Host integration | Disposable 80 GiB pair installed with independent ESPs, Btrfs RAID1 and synchronized md/LUKS swap; marked unselected disk unchanged; 27.1 reached normal runtime with verified `/usr`, encrypted swap, enforcing SELinux and root SSH after prototype configuration repairs | Fresh signed image must reproduce those repairs, cold-home SSH and successful native blessing; then TPM enrollment, degraded boots and replacement |
| Update maintenance | Durable lock/version/state, two-disk hash verification, boot counters/quarantine, Berlin window, bounded ACPI shutdown and abort restoration | Real sysupdate/ESP interruptions, boot failure/watchdog/fallback, external startup policy and retained-state compatibility |
| Local checks | Ruff and shell syntax; 66 tests including disposable GPG signatures, dirty-file signature-slot overwrite, final driver retention, inactive required-service detection, private/public configuration modes, authenticated/idempotent ESP blessing, fallback after failed blessing, supervised activation, native host inventory, interrupted transactions and VM failure recovery | Unit tests do not replace normal-boot and hardware acceptance |
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
The corrected initrd uses that exact-identity path; 27.1 successfully switched
root and activated encrypted mirrored swap. Unattended TPM unlock remains
unvalidated.

With fresh disposable 4 MiB OVMF firmware, Secure Boot, firmware event logging,
nonzero PCR 7/11 and systemd's measured-UKI condition passed. The older 2 MiB test
firmware exposed a TPM but left those PCRs zero and provided no event log; the
preflight now rejects that configuration. No measurement checks were bypassed.

The writable-root prototype verified a fresh inactive homed subvolume account:
the SSH key alone was rejected, key-plus-password authentication through native
PAM activated its home, a remote command wrote there, and cleanup removed the
account. Upstream 262 requires an activation credential even for subvolume homes.
Keyboard-interactive authentication lost the home reference between OpenSSH
processes; native password authentication retained it. Root remains key-only.
These tests used writable prototype SSH/network configuration on 27.1; they do
not establish unattended first boot of the revised image. Native boot blessing
also exposed missing SELinux file permissions on selected ESPs; the narrow image
policy and explicit ESP selection still need a signed-image boot test.

28.1 installed on a fresh disposable pair with preseeded machine identity, the
headless target, readable network configuration, RAID1 data/metadata/system and
clean mirrored swap; the unselected disk remained unchanged. Its first boot
skipped the interactive setup prompts and reached normal userspace. Assessment
then correctly rejected inactive auditd: SELinux denied reading the `/etc/audit`
symlink. The journal also exposed a firewall/socket ordering cycle. Source now
uses the ordinary `/etc` link type for both audit/SELinux factory links and early
firewall dependencies, and verifies the full multi-user transaction during image
builds. Fresh-boot acceptance remains open until those corrections pass.

With those two writable fixture repairs, 28.1 passed assessment and its native
homed cold-home SSH test. Native blessing then exposed an existing GPT-generated
ESP mount with a conflicting FAT SELinux context. Applying uniform mount options
made the stock blessing service succeed with enforcement enabled; source now
aligns all standard ESP mount locations. The software TPM subsequently enrolled
both state volumes and mirrored swap with PCR7 plus signed PCR11; all original
recovery slots still unlocked. A cold boot unlocked storage without console input
or a recovery credential in `/run`. Repeating native blessing then failed because
the UKI was already good and had no counter. Source now treats an authenticated
already-good current entry as success without invoking native counter mutation.
Independent disk boot and a fresh image incorporating all repairs remain required.
These prototype results do not establish fresh-image acceptance.

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
