# Implementation and validation status

ParticleVE is an uncommissioned ParticleOS fork with full upstream Git history,
Fedora 45 and the stable systemd package family. No physical installation disk or
firmware has been modified. Automatic OS preparation and maintenance timers stay
disabled. The owner selected delivery as an uncommissioned candidate; physical
commissioning and enabling automation are outside this delivery.

## Proven disposable behavior

| Area | Evidence |
| --- | --- |
| Build and publication | Four package-scoped GitHub hooks import source changes. OBS signs and publishes complete images and RPMs. Dependency-only rebuild 26.2 advanced the image version without changing Git or the retained-state contract. |
| Verified boot | Fresh signed 35.1 booted with Secure Boot, EROFS/verity, SELinux enforcing, native audit/firewall, encrypted Btrfs RAID1 data/metadata and mirrored encrypted swap. TPM enrollment preserved owner recovery slots; subsequent normal boots unlocked unattended. |
| Native OS update | Packaged 35.1 prepared both disks and activated signed 37.1 through the native coordinator. A running guest exited gracefully before reboot. New boot assessment/blessing completed and the shutdown ledger recorded completion without restoration failures. |
| Virtualization | Final signed 37.1 ran native vmspawn, QEMU/KVM and swtpm in their confined domains with the same per-VM MCS pair. Native nsresourced allocated the TAP; networkd supplied DHCP. CAP_NET_ADMIN was absent from every VM process. Registration, readiness, pinned SSH, DNS and HTTPS worked. |
| Retained state | Guest disk and EFI markers, external unit definitions, disabled startup policy and SSH identity survived restart/update. Native vTPM manufacture succeeded on 37.1, and a persistent NV marker was written/read. Raw disks alone used NOCOW; EFI/vTPM state retained CoW. |
| Accounts | A cold inactive non-root homed subvolume accepted key-plus-password SSH, activated its home and preserved its marker through the OS update. Key-only cold-home login was rejected. Root retained independent key-only SSH and its encrypted home. |
| Confinement | Actual final-image QEMU probes were denied cross-category VM files, host-private files and an unconfined host-service socket. The socket had matching filesystem categories and permissive DAC. swtpm could access matching-category state and was denied another pair. SELinux remained enforcing. |
| Shutdown and scheduling | Native synchronous unit shutdown completed with guest exit zero and storage still mounted. Earlier disposable refusal/late-exit tests kept the host running, reported unsettled guests, and restored only the affected invocation. The native Berlin calendar retained 04:30 across both DST changes, with no catch-up timer. |
| Maintenance and resources | Persistent manual maintenance deferred preparation without changing the running guest invocation. Physical RAM, available RAM, Btrfs allocation/errors/capacity and swap redundancy are reported. Virtual-disk SMART was explicitly unavailable. Low-RAM and SMART-fault guards are tested. |
| Checks | Ruff, formatting, shell syntax and 86 tests pass, including disposable GPG checks, transfer identities, boot blessing, transactions, resources, shutdown and MCS launch contracts. The resolved pinned mkosi configuration passes its build check. |
| Firmware | Native fwupd device/update discovery worked and reported no eligible update. The EFI helper is project-signed. Metadata refresh is separate from supervised installation; no firmware installation was performed. |

## Single-member recovery under test

Signed 37.1 mounted encrypted root and degraded swap from B alone after the
bounded missing-device wait and reached userspace. This confirmed the corrected
initrd readiness rule and required storage ordering. Assessment then exposed a
separate inventory defect: native Btrfs reports the absent recorded device as
`path MISSING`, with zero size and usage. Source now recognizes that exact row
only when its recorded physical disk, partition and mapper are absent. Every
present member still passes mapper, partition and LUKS identity checks. Maintenance
requires two present healthy members. The corrected inventory passed against the
actual read-only survivor and has regression coverage.

The survivor remains isolated from stale disk A after degraded writes. Signed
38.1 was fully authenticated and installed into the survivor's inactive slot
using native sysupdate from recovery. Both the new OS set and retained 37.1 set
passed readback authentication. Its unmodified B-only boot then passed native
assessment, blessing, runtime readiness, TPM unlock and cold homed SSH. Guest disk,
EFI, vTPM NV and SSH markers survived; real host/guest degraded writes passed.
Preparation was rejected without changing the running guest invocation.
No assessment/runtime override was installed. No retained-data migration or
unconfined VM-state relabeling was introduced.

Blank-disk replacement exposed a background Btrfs copy canceled when its service
exited, and stale crypttab state after the new LUKS identity was recorded. Source
now owns the foreground copy without a short timeout and renders crypttab from
the updated installation manifest. Native owner recovery of the canceled test
target completed with zero copy errors; swap resynchronized. All allocated profiles were restored to RAID1 and native
finalization succeeded. The canceled target
was confirmed to have replacement devid 0 and to be absent from mounted sysfs
membership before its partial signature was cleared. The retained survivor was
untouched. Final-image replacement and independent replacement-boot acceptance
remain in progress.

## Scope and remaining validation

The fixture uses two 80 GiB virtio disks, an unselected marker disk, 6 GiB configured
RAM, nested KVM, disposable enrolled 4 MiB OVMF and a private software TPM.
Six GiB is a tested configuration, not an established production minimum.
Generic Intel/AMD microcode, KVM and storage/network drivers remain in the image;
one fixture does not prove varied physical hardware support.

A strict test-only upstream libtpms build was needed for the RSA4096 authorization
key. Fedora libtpms 0.10.2 correctly failed capability preflight; the production
TPM packages and measurement requirements were unchanged. Older 2 MiB test
firmware lacked usable measured-boot evidence and was rejected.

Open acceptance includes replacement/independent-A completion, failed-boot counter
exhaustion and quarantine, live active-usr loss, full interrupted-update boundaries,
multiple-guest maintenance races, pressure-derived RAM minima, Intel/AMD and
controller/NIC variation, real SMART and supported firmware update transports.
Earlier writable diagnostic prototypes are not final-image acceptance. Every
PLAN.md milestone stays open where its complete exit criteria lack evidence.
No production hardware support list or unattended commissioning is claimed.

The ignored `build/acceptance/` directory contains named evidence receipts, pinned
SSH logs and isolated disk/TPM state. It also contains disposable private credentials
and must not be published. Git contains implementation, public trust and this
validation status only.
