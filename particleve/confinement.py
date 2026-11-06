"""Fail-closed native VM launch contract; persistent labels belong to provisioning."""

import os
import re
import stat
from pathlib import Path

from .common import require

MACHINES = Path("/var/lib/machines")
RUNTIME = Path("/run/particleve-vm")
GATE = Path("/run/particleve/vm-start-inhibited")
CONTROLLER = "particleve_vmspawn_t"


def context(value, expected_type):
    parts = value.rstrip("\0\n").split(":", 4)
    require(
        len(parts) == 5 and parts[2] == expected_type and parts[3] == "s0", "unexpected VM SELinux context"
    )
    categories = []
    for item in parts[4].split(","):
        match = re.fullmatch(r"c([0-9]+)(?:\.c([0-9]+))?", item)
        require(match is not None, "invalid VM MCS category")
        first = int(match[1])
        last = int(match[2]) if match[2] else first
        require(0 <= first <= last < 1024 and last - first <= 1, "VM needs exactly two MCS categories")
        categories.extend(range(first, last + 1))
    require(
        len(categories) == 2 and len(set(categories)) == 2, "VM needs exactly two distinct MCS categories"
    )
    return tuple(sorted(categories))


def label(path):
    return os.getxattr(path, "security.selinux", follow_symlinks=False).decode()


def private_directory(path):
    info = path.lstat()
    require(
        stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700,
        f"VM directory must be a root-owned, nonsymlink directory with mode 0700: {path}",
    )
    return info


def start_guard(name):
    require(os.geteuid() == 0, "VM launch requires root")
    require(not GATE.exists(), "VM starts are temporarily inhibited for OS maintenance")
    require(
        Path("/sys/fs/selinux/enforce").read_text().strip() == "1", "VM launch requires SELinux enforcing"
    )
    require(os.access("/dev/kvm", os.R_OK | os.W_OK), "KVM acceleration is required")
    require(re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", name) is not None, "invalid VM instance name")
    unit = f"systemd-vmspawn@{name}.service"
    groups = [
        line[3:] for line in Path("/proc/self/cgroup").read_text().splitlines() if line.startswith("0::")
    ]
    require(len(groups) == 1 and Path(groups[0]).name == unit, "VM guard must run in its owning unit")
    categories = context(Path("/proc/self/attr/current").read_text(), CONTROLLER)
    root = MACHINES / name
    require(private_directory(root).st_ino == 256, "VM root must be a Btrfs subvolume")
    require(context(label(root), "virt_var_lib_t") == categories, "VM subvolume and unit categories differ")
    for other in MACHINES.iterdir():
        if other == root or not other.is_dir():
            continue
        require(not other.is_symlink(), "symlink in VM storage inventory")
        require(
            context(label(other), "virt_var_lib_t") != categories,
            f"VM MCS category pair is already assigned: {other.name}",
        )
    runtime = RUNTIME / name
    private_directory(runtime)
    require(label(runtime).split(":")[2] == "qemu_var_run_t", "unexpected VM runtime directory type")
    # PID1 creates this ephemeral directory at s0. Never relabel retained VM data.
    first, second = categories
    os.setxattr(
        runtime,
        "security.selinux",
        f"system_u:object_r:qemu_var_run_t:s0:c{first},c{second}\0".encode(),
        follow_symlinks=False,
    )


def verify_processes(processes):
    categories = None
    types = set()
    for entry in processes:
        current = Path(f"/proc/{entry['pid']}/attr/current").read_text()
        kind = current.split(":")[2]
        require(
            kind in (CONTROLLER, "svirt_t", "swtpm_t"), "VM unit contains an unexpected or unconfined process"
        )
        pair = context(current, kind)
        if categories is None:
            categories = pair
        require(pair == categories, "VM processes have different MCS categories")
        types.add(kind)
    require(CONTROLLER in types and "svirt_t" in types, "VM controller or confined QEMU is missing")
