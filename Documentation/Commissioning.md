# Commissioning

Automatic OS work is disabled in the factory presets. Commission only the exact
installed image, selected disk pair and installation configuration, after the
acceptance matrix in PLAN.md has passed. `examples/acceptance.json` is an evidence
schema, not a record of completed validation. Fill its image/installation identity,
owner, measured RAM minimum, hardware coverage, gaps and each scenario's evidence
file/hash. A missing, changed or failing scenario blocks commissioning.

Run tests on disposable disks/VMs or the explicitly selected target with console
and independent recovery credentials available. Never substitute unit-test output
for real boot, TPM, Secure Boot, verity, SELinux or guest I/O evidence. Test cold-home
SSH for a non-root homed user (`PYTHONPATH=. python3 tools/check-homed-ssh.py` on the target), root recovery, both boot disks alone, bounded degraded
writes, replacement/profile restoration, corruption rejection, every update boundary,
failed boot/quarantine, Berlin DST/no catch-up and graceful guest refusal/late exits.
Confirm temporary inhibition does not change externally owned startup/restart policy.

For each disposable VM, record the packaged template/arguments, machined ownership,
KVM acceleration, console, disk/network I/O, per-VM subvolume/raw file attributes and
persistent EFI/optional TPM paths. Restart across an OS update and fallback to prove
that retained host software can access current auxiliary state. Btrfs scrub evidence
must explicitly exclude checksum protection of NOCOW raw contents. Exercise pressure
with configured reserves and report minimum host memory measured without counting swap.

Record firmware discovery and helper trust on both ESPs, unsupported devices and
untested transports. If no eligible firmware update exists, mark actual flashing
unvalidated; `firmware_flash.result=no-eligible-update` is accepted only with explicit
evidence. Firmware installation remains supervised after commissioning.

```sh
particleve commission --evidence /var/lib/particleve/evidence/acceptance.json
particleve commission --evidence /var/lib/particleve/evidence/acceptance.json --enable
```

The first command validates evidence and current health. `--enable` binds the record
to configuration and installation hashes and enables the guarded prepare timer and
`particleve-maintenance.timer`. Replacing a disk or changing installation settings
invalidates that binding. `particleve disable-automation` stops the timers and removes
the commissioning marker. Persistent manual maintenance independently inhibits both
preparation and activation under the same durable lock.
