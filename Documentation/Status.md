# Implementation and validation status

ParticleVE is an uncommissioned ParticleOS fork with full upstream Git history,
Fedora 45 and the stable systemd package family. No physical installation disk or
firmware has been modified. Automatic OS preparation and maintenance timers stay
disabled. The owner selected delivery as an uncommissioned candidate; physical
commissioning and enabling automation are outside this delivery.

Candidate implementation and disposable acceptance completed on signed 45.1
(`4db94b572a1f096e192ace7ed480ca26305cb7b1`). That image used kernel
`7.2.15-300.fc45`, systemd `262.1+200+g63511d728-73.1`, QEMU `11.1.3-1.fc45`,
swtpm `0.10.2-1.fc45` and fwupd `2.1.9-1.fc45`. Documentation-only successors
carry the same implementation; the evidence below names the actual tested images.

## Proven disposable behavior

| Area | Evidence |
| --- | --- |
| Build and publication | Four package-scoped GitHub hooks import source changes. OBS signs and publishes complete images and RPMs. Dependency-only rebuild 26.2 advanced the image version without changing Git or the retained-state contract. Source build 45.1 completed automatically after its RPM dependencies were published, using the original repository layout and flags. |
| Verified boot | Fresh signed 35.1 booted with Secure Boot, EROFS/verity, SELinux enforcing, native audit/firewall, encrypted Btrfs RAID1 data/metadata and mirrored encrypted swap. TPM enrollment preserved owner recovery slots; subsequent normal boots unlocked unattended. |
| Native OS update | Packaged 35.1 prepared both disks and activated signed 37.1 through the native coordinator. A running guest exited gracefully before reboot. New boot assessment/blessing completed and the shutdown ledger recorded completion without restoration failures. |
| Virtualization | Final signed 37.1 ran native vmspawn, QEMU/KVM and swtpm in their confined domains with the same per-VM MCS pair. Native nsresourced allocated the TAP; networkd supplied DHCP. CAP_NET_ADMIN was absent from every VM process. Registration, readiness, pinned SSH, DNS and HTTPS worked. |
| Retained state | Guest disk and EFI markers, external unit definitions, disabled startup policy and SSH identity survived restart/update. Native vTPM manufacture succeeded on 37.1, and a persistent NV marker was written/read. Raw disks alone used NOCOW; EFI/vTPM state retained CoW. |
| Accounts | A cold inactive non-root homed subvolume accepted key-plus-password SSH, activated its home and preserved its marker through the OS update. Key-only cold-home login was rejected. Root retained independent key-only SSH and its encrypted home. |
| Confinement | Actual final-image QEMU probes were denied cross-category VM files, host-private files and an unconfined host-service socket. The socket had matching filesystem categories and permissive DAC. swtpm could access matching-category state and was denied another pair. SELinux remained enforcing. |
| Shutdown and scheduling | Native synchronous unit shutdown completed with guest exit zero and storage still mounted. Two real confined guests passed refusal, late-exit and interrupted-maintenance recovery: the host stayed running, only the affected stopped guest restarted, and concurrent starts were blocked. The native Berlin calendar retained 04:30 across both DST changes, with no catch-up timer. |
| Maintenance and resources | Persistent manual maintenance and real memory pressure below the 1 GiB reserve deferred preparation without changing either guest invocation or rebooting. Physical RAM, Btrfs allocation/errors/capacity and swap redundancy are reported. Native zswap stored and recovered 4,096 disposable pages with byte-identical readback. Virtual-disk SMART was explicitly unavailable; SMART-fault guards have regression coverage. |
| Checks | Ruff, formatting, shell syntax and 95 tests pass, including disposable GPG checks, transfer identities, boot blessing, transactions, resources, shutdown and MCS launch contracts. The resolved pinned mkosi configuration passes its build check. |
| Firmware | On signed 44.1, native fwupd refreshed LVFS metadata, discovered both selected ESPs and reported no eligible update. Its installed EFI helper passed project-certificate verification. Metadata refresh is separate from supervised installation; no firmware installation was performed. |

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

## Native boot-counter fallback

An initial 39.1 failure experiment exposed an exact-version loader default that
forced an exhausted candidate. Source now pins the current release during
preparation, then selects the ParticleVE namespace at activation so native boot
ordering can prefer a viable retained release. It refuses an exhausted candidate
and never resets its counters.

The real corrected-image test prepared and activated 42.2 from 42.1 with both
guests running. Both exited gracefully before reboot. Reversible loss of only
the disposable management carrier caused three native assessment failures and
reboots. After carrier restoration, systemd-boot selected retained 42.1. Native
assessment, blessing and runtime readiness passed; pending state cleared and
42.2 was durably quarantined on both ESPs. The booted ESP retained `+0-3` in its
rejected filename; the other retained its independent `+3` count. No assessment
or policy override was used. Both disabled guest startup policies were honored.
After manual start, both guests retained their SSH/disk identities; EFI/vTPM NV
and both degraded-write markers survived. Cold homed SSH passed after fallback.
See the upstream [boot-counting contract](https://www.freedesktop.org/software/systemd/man/latest/systemd-boot.html#Boot%20Counting).

## Interrupted acquisition correction

A real 43.1 A-side usr transfer was interrupted while the old 42.1 set remained
protected. Both retained boot paths still authenticated and neither ESP exposed
an incomplete candidate. A subsequent native prepare exposed the selected
sysupdate's requirement to vacuum an already acquired partial set before retry.

Using the exact selected-disk definitions, native vacuum removed only the
pending signature/verity resources and partial usr resource. The running release
still authenticated on both disks. Source now performs this native cleanup before
each required transfer, with the running version protected in the same definitions.
All twelve A/B signature, verity, usr, UKI, bootloader and fallback-loader
interruption boundaries passed on 42.1 while preparing 43.1. The retained sets
authenticated, incomplete candidates remained unreferenced, and running guest
invocations stayed unchanged. These tests used the explicit native vacuum
prototype. Signed 44.1 then passed the packaged correction: after a real partial
45.1 usr acquisition, plain `particleve prepare --manual` completed and verified
both boot paths without operator vacuum, guest restarts or a host reboot. An ordinary
reboot during preparation preserved pending state and honored disabled guest
startup policies. No writable-root or guest-data recovery/migration is involved.

## Native guest console correction

A real read-only serial-console launch exposed missing PTY access despite the
working headless runtime. Signed 43.1 then launched the native read-only console,
but inspection found its PTY lacked categories. Source now quarantines newly
allocated PTYs above every valid VM category pair. A guarded native QEMU handoff
labels inherited console descriptors with the owning pair before transitioning
to confined QEMU. It preserves native arguments and descriptors and rejects
unexpected labels or launch paths. Signed 45.1 ran the native read-only serial
console with its exact category pair. Real confined QEMU opened a matching-pair
test terminal and was denied both the other running guest's console and a
controlled foreign-pair terminal. The loaded kernel's creation decision confirms
the all-category quarantine label, and its access decision denies QEMU all
open/read/write access to that label. The native guest was restored after the
probes; the other guest's invocation stayed unchanged. SELinux remained enforcing.
Both guests subsequently passed pinned SSH and retained-marker checks; the first
retained its EFI variable and vTPM NV value. Cold homed SSH passed on 45.1. Final
checks verified both authenticated boot paths, healthy encrypted RAID1/swap,
NOCOW only on raw guest disks, CoW on auxiliary files, unchanged unselected-disk
hash, disabled external startup policies and inactive automatic OS timers. No
temporary probe or private-device unit override remained.

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

Open acceptance includes pressure-derived RAM minima, Intel/AMD and
controller/NIC variation, real SMART and supported firmware update transports.
Earlier writable diagnostic prototypes are not final-image acceptance. Every
PLAN.md milestone stays open where its complete exit criteria lack evidence.
No production hardware support list or unattended commissioning is claimed.

The ignored `build/acceptance/` directory contains named evidence receipts, pinned
SSH logs and isolated disk/TPM state. It also contains disposable private credentials
and must not be published. Git contains implementation, public trust and this
validation status only.
