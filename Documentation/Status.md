# Implementation and validation status

ParticleVE is implemented as a native ParticleOS fork with full upstream Git
history, Fedora 45, stable systemd, dual-disk storage and coordinated updates.
This is an uncommissioned candidate. Automatic OS timers remain disabled.
PLAN.md milestones remain open until their complete exit criteria have evidence.

| Area | Evidence | Remaining acceptance |
| --- | --- | --- |
| Sources and OBS | Four scoped GitHub source hooks exercised; persistent OBS signing; RPMs built; signed public image 30.1 verified; dependency-only integration rebuild produced distinguishable 26.2 with unchanged Git and persistent-state contracts | Complete fresh-image acceptance of the latest source |
| Native boot | Prototype 28.1 booted unattended from either selected ESP with Secure Boot, measured PCR7/11, verity, TPM unlock, SELinux enforcing, homed SSH, RAID1 data/metadata and encrypted mirrored swap | Fresh installation incorporating all repairs; sole-member boots, degraded writes and replacement |
| Virtualization | Packaged vmspawn template, nested KVM, machined registration, TAP/DHCP, readiness, disk/network I/O and persistent guest EFI state; only raw disk has NOCOW | Guest vTPM and broader runtime/confinement acceptance |
| Native update | Both authenticated 30.1 sets prepared while host/guest ran; supervised activation gracefully stopped the guest, booted 30.1 unattended, passed assessment/blessing and cleared pending state | Interruption boundaries, refusing/late guests, actual watchdog/fallback and retained-state compatibility |
| VM recovery | Real concurrent template start refused; real graceful ACPI poweroff, refusal and late-exit reconciliation passed; guest disk/EFI markers and pinned SSH identity survived restart and host update; disabled permanent startup policy was preserved | Multiple-guest and fresh-image shutdown-ordering acceptance |
| Resources | Btrfs profiles/errors/capacity, swap redundancy, physical RAM availability and selected-disk SMART reporting; memory reserve and SMART-fault maintenance guards; real virtual-disk SMART unavailability reported explicitly | Measured minimum physical RAM, real disk/controller health and pressure acceptance |
| Checks | Ruff, formatting, shell syntax and 76 tests pass, including disposable GPG verification, native transfer UUIDs, boot blessing, transaction recovery, resource guards and VM shutdown logic | Tests do not establish hardware commissioning |
| Firmware | Signed EFI helper; native device/update discovery; metadata-only refresh; persistent manual-maintenance exclusion | Real supported update/transport, or recorded lack of eligible update; either-disk ESP selection |

## Scope of the disposable evidence

The isolated host has two 80 GiB virtio disks, an unselected marker disk, 6 GiB
configured RAM, nested KVM, a software TPM and disposable enrolled 4 MiB OVMF
firmware. No physical installation disk or firmware has been modified. The image
retains generic Intel/AMD and storage/network drivers; this fixture does not prove
varied hardware support.

A strict test-only upstream libtpms build was needed for the project's RSA4096
TPM authorization key. Fedora libtpms 0.10.2 correctly failed the capability
preflight. Older 2 MiB test firmware exposed no event log or nonzero PCR7/11 and
was rejected. Production TPM packages and measurement requirements were unchanged.
All original owner recovery slots were tested after TPM enrollment.

28.1 is a repaired writable-root prototype. First boot exposed an audit factory
symlink label, early firewall ordering, inconsistent ESP mount contexts and
already-good boot blessing behavior. Source fixes all four; a fresh complete
image must pass without those writable fixture repairs. The prototype also used
the revised DHCP input policy before restarting its guest. Normal host shutdown
then exposed vmspawn's SIGKILL fallback when SSH injection is disabled. A narrow
template stop helper now sends native ACPI poweroff and waits for all unit
processes, keeping storage available; ordinary shutdown waits for owner assistance
if a guest refuses. Automatic maintenance retains its bounded abort/recovery path.
Fresh-image acceptance of the helper remains required. The signed `/usr`
remained read-only and SELinux remained enforcing throughout.

Native sysupdate testing exposed explicit path-anchor and compact-UUID filename
capture defects. Source now uses root-relative absolute paths and authenticated
explicit partition UUIDs. Corrected definitions were exercised in process memory
on 28.1; an earlier inactive diagnostic slot was repaired only after payload and
fallback verification. No retained-data migration was added.

Supervised activation used the OBS-signed integration 30.1 RPM's 18 Python modules
in a private temporary directory, verified against the project key and published
source 74fe527. It retained every disk, firmware, compatibility and graceful VM
shutdown guard; no commissioning evidence or automatic enablement was forged.
The actual 28.1-to-30.1 boot passed native assessment and blessing and reconciled
the shutdown ledger. This does not establish production fallback: the older
28.1 image has the already-good blessing defect described above.

A cold inactive homed subvolume account accepted key-plus-password SSH through
native PAM, activated its home and wrote there; key-only authentication was
rejected. Root remains key-only and keeps its home on encrypted writable state.
Non-root login users must come from homed. System service accounts remain native.

Packaged vmspawn/QEMU processes run in `unconfined_service_t`; global enforcing
mode alone does not establish VM process confinement. Commissioning must review
that upstream policy coverage. Guest vTPM tools are now explicit image inputs;
persistent guest vTPM acceptance is still open.

The exact initrd watchdog units survived emergency isolation in a real shortened
disposable test. Actual normal-boot cancellation, full timeout/counter exhaustion
and fallback remain unvalidated. Boot from one ESP with both disks present does
not establish boot with its peer absent or which duplicate `/usr` was selected.

## Commissioning remains disabled

Outstanding work includes a fresh complete baseline, single-member boots and
replacement, failed-boot/fallback scenarios, native multi-guest refusal/late-exit
cases, guest vTPM persistence, measured resource minima, Intel/AMD and controller/
NIC variation, supervised supported firmware maintenance, and unattended update/
no-update windows. The generic UKI uses tty0; arbitrary serial kernel/initrd
consoles have not been validated. No supported production hardware list is claimed.

The workspace's ignored `build/acceptance/` directory contains isolated VM state,
public-key-pinned SSH logs and named evidence receipts. It also contains private
disposable credentials; do not publish that directory. Source control contains
only the implementation, public trust and this explicit validation status.
