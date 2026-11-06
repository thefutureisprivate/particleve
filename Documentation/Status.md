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
| Shutdown and scheduling | Native synchronous unit shutdown completed with guest exit zero and storage still mounted. Two real confined guests passed refusal, late-exit and interrupted-maintenance recovery: the host stayed running, only the affected stopped guest restarted, and concurrent starts were blocked. The native Berlin calendar retained 04:30 across both DST changes, with no catch-up timer. |
| Maintenance and resources | Persistent manual maintenance deferred preparation without changing the running guest invocation. Physical RAM, available RAM, Btrfs allocation/errors/capacity and swap redundancy are reported. Virtual-disk SMART was explicitly unavailable. Low-RAM and SMART-fault guards are tested. |
| Checks | Ruff, formatting, shell syntax and 91 tests pass, including disposable GPG checks, transfer identities, boot blessing, transactions, resources, shutdown and MCS launch contracts. The resolved pinned mkosi configuration passes its build check. |
| Firmware | Native fwupd device/update discovery worked and reported no eligible update. The EFI helper is project-signed. Metadata refresh is separate from supervised installation; no firmware installation was performed. |

## Single-member and disk-replacement validation

Signed 42.1 booted unattended with A alone and B alone, using native assessment,
blessing and runtime readiness without entrypoint overrides. Cold homed SSH and
real host/guest degraded writes passed on each side. Guest disk, EFI and vTPM NV
state survived. The earlier signed 38.1 B-only test independently covered the
bounded missing-device wait and corrected native `path MISSING` inventory.

Each stale peer stayed offline after degraded writes. Both roles were replaced
with new blank 80 GiB virtual disks using the installed 42.1 CLI. Foreground
Btrfs copying completed with zero copy errors; crypttab was refreshed from each
new LUKS identity, mirrored swap resynchronized, all allocated data/metadata/system
profiles returned to RAID1, and native finalization succeeded. New A and B boot
paths were exercised. The final pair is coherent; no stale member was rejoined.

The active A virtual PCI disk was also removed from a healthy running host, with
both guests stopped. Native reboot succeeded and B booted unattended with A
absent. Recorded errors belonged to the removed member; the survivor retained
both host and guest A-only writes. This tests recovery after active-`/usr` loss,
without promising continuous operation or graceful workload survival during it.
No retained-data migration or unconfined VM-state relabeling was introduced.

## Explicit TPM enrollment policy

Independent A boot on 39.1 exposed implicit combination of PCR7/signed-PCR11 with
an existing pcrlock policy whose credential was ESP-local. Enrollment now passes
an explicit empty pcrlock option and reads back native token metadata. A
qualifying token must contain SHA256 PCR7, signed PCR11 authorization for the
immutable configured key, and no pcrlock or PIN. Commissioning repeats the live
checks so an older receipt cannot substitute for the selected policy.

Packaged signed 42.1 enrollment and both native replacement paths passed this
audit. Unattended A-only and B-only boots passed. On the restored pair, native
owner-recovery passphrase checks succeeded for both state volumes and mirrored
swap; their current UUIDs match the enrollment receipt. Recovery slots were
preserved, other owner slots were not erased, and volatile owner key files were
removed after each operation.

## Boot-counter selection correction

A real 39.1 activation stopped both guests gracefully, then a reversible QEMU
management-carrier fault caused three native assessment failures and reboots.
Restoring the carrier for the fourth boot revealed that the version-specific
loader.conf default still forced the exhausted entry. The retained EFI variable
reported its original `+0-4.efi` boot-count path. No assessment or policy override
was used. The host then passed normal 39.1 assessment and blessing after carrier
restoration, so this is not recorded as successful fallback.

Source keeps the current version pinned while preparation is incomplete. After
both complete releases are exposed, activation selects the ParticleVE namespace
and lets native boot ordering prefer a viable release over an exhausted one.
It refuses an already exhausted candidate and never resets its counters.
A native temporary GPT ESP probe with real signed UKIs confirmed that the old
pattern selects the exhausted 39.1 entry, while the corrected pattern selects
the good 38.1 fallback without changing either real ESP or EFI variables. Fresh
signed-image retry, fallback and quarantine acceptance remain required.
See the upstream [boot-counting contract](https://www.freedesktop.org/software/systemd/man/latest/systemd-boot.html#Boot%20Counting).

## Native guest console correction

A real read-only serial-console launch exposed missing PTY access despite the
working headless runtime. Source adds only the PTY multiplexer device and a
dedicated controller PTY type usable by confined QEMU under its existing MCS
constraints. Corrected-image console operation and cross-category PTY rejection
remain to be validated. The disposable prototype unit was restored before the
failed-boot test; SELinux remained enforcing.

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

Open acceptance includes failed-boot counter exhaustion and quarantine, native
serial-console operation, full interrupted-update boundaries,
pressure-derived RAM minima, Intel/AMD and
controller/NIC variation, real SMART and supported firmware update transports.
Earlier writable diagnostic prototypes are not final-image acceptance. Every
PLAN.md milestone stays open where its complete exit criteria lack evidence.
No production hardware support list or unattended commissioning is claimed.

The ignored `build/acceptance/` directory contains named evidence receipts, pinned
SSH logs and isolated disk/TPM state. It also contains disposable private credentials
and must not be published. Git contains implementation, public trust and this
validation status only.
