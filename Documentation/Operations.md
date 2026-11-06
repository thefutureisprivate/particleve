# Installation and operation

Use an owner-controlled recovery environment with the required packaged tools,
UEFI, Secure Boot, TPM2 and KVM support. Copy `examples/host.json` outside the
checkout and configure stable whole-disk by-id paths and serials, permanent NIC
MACs, network topology, management allowlists, SSH public keys, resource reserves
and the real signed feed. Inspect a read-only preflight before preparing a plan.

```sh
particleve --config /run/host.json preflight
particleve --config /run/host.json plan --release-dir /run/release --output /run/install-plan.json
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

`particleve status` reports durable update/maintenance state and observed storage
profiles, capacity, errors and swap redundancy. Keep configured byte/percentage
reserves available; degraded profiles, errors, resync, replacement or insufficient
headroom defer automatic work. Root journal storage and update caches are bounded.

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

For disk replacement, enter persistent maintenance, physically identify the failed
member and select its role. `replace-disk --role … --disk /dev/disk/by-id/… --serial …`
first prints a deterministic reviewable erasing plan; the second invocation needs
its exact confirmation and independent recovery-key file. It replaces the Btrfs
device, resynchronizes swap and provisions complete OS slots/ESP on the new disk.
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
