# Installation and operation

Use an owner-controlled recovery environment with the required packaged tools,
UEFI, Secure Boot, TPM2 and KVM support. Copy `examples/host.json` outside the
checkout and configure stable whole-disk by-id paths and serials, permanent NIC
MACs, network topology, management allowlists, SSH public keys, resource reserves
and the real signed feed. Inspect a read-only preflight before preparing a plan.
`render-network --output DIRECTORY` stages networkd configuration and a `host.nft`
policy preview. At boot, `apply-firewall` renders the running image's policy from
the bound host settings and sends it directly to nftables. Generic firewall fixes
therefore follow the OS without replacing persistent installation settings.
The host-input policy allows DHCP requests on native `vt-*` and broker `ns-*` TAPs;
management SSH remains restricted to the configured management sources.
Install the ParticleVE integration RPM from the owner-trusted OBS repository;
it includes the public release-verification material. Authenticate its repository
key independently before importing it. `fetch-release` verifies the signed index,
complete artifact hashes, EFI signatures and UKI metadata before returning a
release directory; it does not change installation disks.

```sh
particleve --config /run/host.json preflight
particleve --config /run/host.json fetch-release --output /run/releases
particleve --config /run/host.json plan --release-dir /run/releases/VERSION --output /run/install-plan.json
```

Review the complete plan, including serials, smaller-disk sizing and every
partition. Installation deliberately erases both selected disks and requires the
exact plan digest. No unselected device is a target. Keep an independent recovery
passphrase in a root-owned mode-0600 regular file under `/run`; keep its durable
copy off the host. Its file bytes must be printable ASCII without a trailing
newline, so the same passphrase can unlock storage at the recovery console. Pass it using `install --recovery-key-file`, never a command-line
secret value. Run `particleve install --help` for the required plan/confirmation
arguments. Interrupted installations require owner recovery; they are not
silently reformatted or migrated.

Each state partition is independently LUKS2 encrypted. On the first installed
boot, enter the owner recovery passphrase at the console. From that verified
normal boot, provide the passphrase file in `/run` and enroll PCR7 plus signed
PCR11 authorization:

```sh
particleve enroll-tpm --recovery-key-file /run/owner-recovery-passphrase
```

Enrollment explicitly disables automatic pcrlock-policy discovery. It reads back
the written token and requires SHA256 PCR7, signed PCR11, and no pcrlock or PIN
before recording success. This is the selected disk-unlock policy; an unrelated
machine pcrlock policy must not silently add an ESP-local credential dependency.
Independent recovery slots remain intact. See the native
[enrollment defaults](https://www.freedesktop.org/software/systemd/man/262/systemd-cryptenroll.html).

The normal initrd has a five-minute boot deadline, cancelled at switch-root.
Its timer survives emergency isolation. Root discovery allows up to four minutes
for the independently encrypted state members and their owner recovery prompts.
If it cannot reach the writable root and verified `/usr`, it requests another
boot attempt before guest runtime access. Use the independent recovery environment
for extended repair rather than waiting indefinitely in a failed normal initrd.

The recovery installer deliberately does not bind its own PCR7 measurements.
Enrollment verifies both installed boot paths and retains all recovery slots.
Reboot and prove unattended unlock from each disk before commissioning. Both mappings form a single Btrfs filesystem with RAID1 data and
metadata. The writable root is never factory-reset or rewound during OS fallback.
Upstream sysusers/tmpfiles initializes it and links generic configuration to
`/usr/share/factory/etc`, allowing PAM/SSH/trust defaults to follow OS updates.
Only installation-specific settings are written as persistent overrides.
`/var` and `/var/lib/machines` are subvolumes. There is no separate home partition
or VM volume manager. Swap alone uses md RAID1 followed by LUKS2 and block swap.
The initrd discovers explicit partition labels, checks encrypted installation
identities and waits for missing members for a configured bounded interval.
Present-but-locked or wrong devices fail; a genuinely absent member permits an
explicit degraded mount. Automatic activation requires a healthy two-disk pair.

Root's home is `/root`, on the encrypted writable root. All non-root login
accounts must be created through upstream `homectl`, using `--storage=subvolume`.
For example, run interactively on the installed host:

```sh
homectl create alice --storage=subvolume --ssh-authorized-keys=@/run/alice.pub
```

Store SSH keys in the user record, so lookup works while a home is inactive.
The host's encryption protects subvolume storage. Native homed still requires
the account's password to activate an inactive home. Non-root SSH therefore
requires both a public key and password authentication through PAM; enter
the password chosen by `homectl` when prompted. Root uses public-key authentication.
SSH uses upstream `userdbctl ssh-authorized-keys` and PAM account/session checks.
Classic non-root login accounts fail the homed account gate. System service
accounts remain ordinary non-login accounts. `particleve check-users` audits the
local passwd database without mistaking NSS-provided homed users for classic
accounts. Test an inactive home, a fresh SSH connection and a host reboot before
relying on remote administration. Keep independent console recovery available.

External configuration owns VM definitions and startup policy. Use the packaged
`systemd-vmspawn@.service` template and keep machined registration/cgroup ownership
intact. Place each raw image in its own externally created subvolume under
`/var/lib/machines`. Keep that VM's persistent EFI variable store and optional
swtpm state on ordinary CoW files in its subvolume. Set `chattr +C` on each empty
raw disk file **before writing it**, then confirm attributes. Never apply NOCOW to
the entire machines directory. NOCOW raw contents lose Btrfs data checksums and
compression; scrub cannot detect or repair corruption in those contents. Normal
host and EFI/vTPM files keep CoW/checksums. Use the exact packaged vmspawn/QEMU
options supported by the release and record persistent-state paths in acceptance
evidence. Guest workload provisioning and backups are outside ParticleVE.

Each newly provisioned VM needs a permanent, unique pair of SELinux MCS categories.
External provisioning labels its root subvolume `virt_var_lib_t`, mode 0700 and
owned by root; its raw disks, seed media and precreated EFI variable file use
`svirt_image_t`. Its TPM directory uses `virt_var_lib_t`. All these labels carry
the same pair, for example `s0:c10,c20`. Do not recursively relabel a running or
retained VM. Changes to an existing VM's labels or auxiliary state need an
explicit retained-data review; ParticleVE supplies no migration.

The external instance drop-in must set the matching process context:

```ini
[Service]
SELinuxContext=system_u:system_r:particleve_vmspawn_t:s0:c10,c20
```

The mandatory internal launch guard rejects missing/mismatched categories,
duplicate category pairs, nonprivate directories, disabled enforcement and absent
KVM before launching QEMU. It labels only PID1's temporary per-VM runtime
directory. The packaged policy transitions QEMU into `svirt_t` and swtpm into
`swtpm_t`, with MCS constraints on both. The trusted vmspawn controller has its
own confined domain. Maintenance verifies actual process labels and category
agreement; an unconfined or unexpected process blocks activation.

Keep the template's private `/tmp` and `/var/tmp` bindings, launch/stop helpers,
namespace-broker dependency and capability restriction when supplying external
VM arguments. Native nsresourced allocates the TAP descriptor; `CAP_NET_ADMIN`
is removed from the whole VM unit. The policy is compiled during the integration
RPM build and incorporated into the image's factory policy; policy development
tools are not runtime inputs.

The host's template drop-in sends native ACPI poweroff and waits for every VM
process before completing a normal unit stop or host shutdown. It uses an
unbounded stop timeout so a refusing guest needs owner assistance instead of
falling through to vmspawn's signal handler, which kills QEMU when SSH injection
is disabled. Keep this synchronous `ExecStop` when overriding VM arguments.
Inspection errors retain the wait instead of falling through to signals.
Automatic maintenance retains its separate bounded refusal/recovery transaction
while the host is still running; it never enters host shutdown with live VMs.
The selected native interface supports `--efi-nvram-state=PATH` for a persistent
file and `--tpm-state=PATH` for a persistent directory. Keep both within that VM's
subvolume, with normal CoW; the `swtpm-tools` package supplies native TPM
manufacturing and per-VM certificate setup. Test guest readiness notification,
registration, disk/network I/O and restart persistence before commissioning.

`particleve status` reports durable update/maintenance state, observed storage
profiles, capacity, errors, swap redundancy, physical memory and selected-disk
SMART data. Maintenance compares kernel `MemAvailable` with the installation's
`maintenance.minimum_available_ram_mib` (default 1024); swap does not count toward
that reserve. Validation never inserts defaults into the installation JSON or
changes its recorded identity.
The example's 1024 MiB reserve is a configurable starting point, not a measured
hardware minimum. Set it from commissioning measurements. Low available RAM or a
reported SMART fault defers preparation and activation before touching guests.
SMART queries are read-only and use each recorded whole-disk identity. Device
errors, unsupported transports and virtual disks with no SMART data appear as
`unavailable`, never as passed. Record those monitoring gaps at commissioning;
unavailable SMART alone does not block maintenance. Exit-status health bits follow
the [upstream smartctl interface](https://github.com/smartmontools/smartmontools/blob/main/src/smartctl.8.in).
Keep configured byte/percentage reserves available; degraded profiles, errors,
resync, replacement or insufficient headroom defer automatic work. Root journal
storage and update caches are bounded.

Automatic preparation fixes one signed release version, verifies both explicit
disk targets and hashes raw readback before exposing either new UKI. Existing
boot counts and non-OS ESP files are preserved. At 04:30 Berlin time the dedicated
maintenance service rechecks eligibility before touching guests. It temporarily
inhibits template starts/restarts, inventories actual units/machines/processes,
sends ACPI poweroff and waits for actual process exits. Refusal, late/unexpected
restarts, firmware staging or failed reboot queuing cancels activation. Only VMs
stopped by this attempt are restored; failed restoration is durable and reported.
No VM is force-killed. After a successful host reboot external startup policy
applies; the coordinator does not enable or restore the last running set.

Use `particleve recover-vms` to reconcile an interrupted attempt. Inspect reported
late exits/restoration failures before retrying. Boot health assessment gates
blessing; failed candidates exhaust bounded attempts and fall back. The retained
OS quarantines failed releases before VM runtime access. Changed Btrfs/systemd/
QEMU/firmware state contracts require explicit evidence that the retained OS can
read current state; no writable-state or guest-state migration is automatic.

Before commissioning, supervised update acceptance uses `particleve prepare
--manual`, then `particleve activate --manual`. Manual activation starts immediately
and permits an uncommissioned host; it retains firmware exclusion, complete
two-disk verification, a blessed fallback and graceful VM shutdown/restoration.
It does not enable either automatic timer. The timer always uses plain `activate`
and requires commissioning and the 04:30 window.

For disk replacement, enter persistent maintenance, physically identify the failed
member and select its role. `replace-disk --role … --disk /dev/disk/by-id/… --serial …`
first prints a deterministic reviewable erasing plan; the second invocation needs
its exact confirmation and independent recovery-key file. It refreshes crypttab
from the new LUKS identities, waits in the foreground for the Btrfs device copy,
resynchronizes swap and provisions complete OS slots/ESP on the new disk. Keep the
owner session or transient service alive until it returns; large devices can take
hours. Do not impose a short service runtime limit on that copy.
`finalize-replacement` refuses completion until replacement/resync finish and all
allocated Btrfs data/metadata/system profiles are RAID1. Interrupted replacement
requires owner review of its durable journal. Test both independent boot paths
and run `enroll-tpm` under maintenance to refresh enrollment evidence for the
changed LUKS device set. Recommission before enabling automation again.

Losing the disk serving active verified `/usr` can interrupt operation even when
writable RAID1 survives. Use the other firmware boot path or independent recovery
environment, unlock surviving storage with the owner secret if TPM authorization
is unavailable, and repair through the documented replacement path. Never enroll
the recovery environment into normal unattended PCR authorization.

Firmware metadata refresh may run automatically. Before staging/installing
firmware, trust-database changes, or selecting a firmware reboot, enter:

```sh
particleve maintenance enter --reason 'supervised firmware maintenance'
fwupdmgr get-devices
fwupdmgr get-updates
```

The owner selects the update, ESP and reboot and verifies actual device results,
Secure Boot and TPM unlock afterward. Unsupported devices/transports must be
recorded. Capsule files and BootNext block OS work and are preserved. Leave using
`particleve maintenance leave --reviewed` only after staged firmware is clear and
health checks pass. No firmware installation command is scheduled automatically.
