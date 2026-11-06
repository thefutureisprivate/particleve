# ParticleVE

ParticleVE is a headless Fedora 45 hypervisor fork of
[ParticleOS](https://github.com/systemd/particleos), retaining its Git history
at `b605add797ba65853eb79f8170c4a5743a6f4b1f`. The native mkosi configuration
selects `particleve`. It uses the complete upstream OBS stable systemd family,
systemd-vmspawn's packaged service template, machined/machinectl, and QEMU/KVM.
The original documentation is preserved in [Upstream.md](Documentation/Upstream.md).

Each explicitly selected boot disk holds an independent ESP and two verified
EROFS `/usr` slots. Independently LUKS2-encrypted state partitions form native
Btrfs data/metadata RAID1, including the writable root, `/var`, homes and VM files.
Separate md RAID1 backs encrypted block swap and zswap. Root reset and writable
state rollback are disabled. Loss of the active `/usr` disk may require a reboot.

Every non-root login account uses upstream systemd-homed. Home subvolumes inherit
the host's disk encryption; public SSH keys live in homed user records and are
retrieved by upstream userdb. Root's recovery home remains `/root`. SSH, console,
TPM, disk replacement and fallback must pass commissioning on the actual host.

This is an **uncommissioned implementation**. The fwupd EFI helper has built and
been signed in the [ParticleVE OBS project](https://build.opensuse.org/project/show/home:thefutureisprivate:particleve).
A complete signed image and the hardware acceptance matrix are still release
gates. No installation disks or firmware have been altered. x86-64/v2 and example
resource thresholds are candidate settings; measured minima remain unpublished.
See [Status.md](Documentation/Status.md) for the exact validation boundary.

```sh
make check                    # Python 3.14+, Ruff, GnuPG
make sources                  # fetch pinned upstream build inputs
PYTHONPATH=. python3 tools/configure-build.py --site obs/site.json
make summary                  # validate resolved runtime/initrd/tools configuration
```

Build inputs and public trust are committed. Private signing material stays in
OBS. Installation-specific disk identities, networking, keys and recovery
credentials stay outside the generic image. Examples deliberately contain
unusable identities and addresses.

The coordinator prepares one authenticated release on both disks under a durable
lock. Its dedicated timer can request a reboot at 04:30 Europe/Berlin only after
readiness checks and confirmed graceful VM exits. Aborted attempts restore only
VMs stopped by that attempt and report failures. External configuration owns VM
storage, units, startup and workloads. Firmware installation stays supervised;
only metadata refresh is automatic. Automatic OS timers remain disabled until
commissioning succeeds.

See [builds](Documentation/Build.md), [operations](Documentation/Operations.md),
and [commissioning](Documentation/Commissioning.md). LGPL-2.1-or-later is retained.
