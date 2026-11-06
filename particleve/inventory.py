"""Read-only platform discovery. No partitioning or firmware mutation here."""

import fcntl
import json
import os
import platform
import shutil
from pathlib import Path

from .common import Error, require, run

INSTALL_TOOLS = (
    "lsblk",
    "sfdisk",
    "udevadm",
    "mdadm",
    "cryptsetup",
    "systemd-cryptenroll",
    "mkfs.btrfs",
    "btrfs",
    "mkfs.vfat",
    "mkswap",
    "mount",
    "umount",
    "efibootmgr",
    "sbverify",
    "gpgv",
    "bootctl",
    "restorecon",
    "setfiles",
    "veritysetup",
    "blkid",
    "nft",
)


def block_tree(path=None):
    args = [
        "lsblk",
        "--json",
        "--bytes",
        "--paths",
        "--output",
        "NAME,TYPE,SIZE,SERIAL,WWN,LOG-SEC,PHY-SEC,RO,RM,MOUNTPOINTS,PKNAME,PARTN,PARTUUID,PARTLABEL,PTUUID",
    ]
    if path:
        args += [path]
    return json.loads(run(args).stdout)["blockdevices"]


def walk(tree):
    for node in tree:
        yield node
        yield from walk(node.get("children", []))


def observe_disk(selected, *, unused=False):
    path = Path(selected["path"])
    require(path.is_symlink(), f"stable disk identity does not exist: {path}")
    nodes = block_tree(path)
    require(len(nodes) == 1, f"ambiguous selected disk: {path}")
    disk = nodes[0]
    require(
        disk["type"] == "disk" and not disk["ro"] and not disk["rm"], f"not a writable fixed disk: {path}"
    )
    require((disk["serial"] or "").strip() == selected["serial"], f"disk serial changed: {path}")
    if unused:
        for node in walk(nodes):
            require(
                not any(node.get("mountpoints") or []), f"selected disk is mounted/in use: {node['name']}"
            )
            require(node["type"] in ("disk", "part"), f"selected disk has active holders: {node['name']}")
            holders = Path("/sys/class/block") / Path(node["name"]).name / "holders"
            require(
                not holders.exists() or not list(holders.iterdir()),
                f"selected disk has holders: {node['name']}",
            )
    stat = path.stat()
    return {
        "identity": f"{os.major(stat.st_rdev)}:{os.minor(stat.st_rdev)}",
        "size": disk["size"],
        "serial": disk["serial"].strip(),
        "wwn": disk["wwn"],
        "logical_sector": disk["log-sec"],
        "physical_sector": disk["phy-sec"],
    }


def secure_boot():
    variables = list(Path("/sys/firmware/efi/efivars").glob("SecureBoot-*"))
    return len(variables) == 1 and variables[0].read_bytes()[4:] == b"\x01"


def kvm_available():
    try:
        with open("/dev/kvm", "rb", buffering=0) as stream:
            return fcntl.ioctl(stream, 0xAE00) == 12  # KVM_GET_API_VERSION
    except OSError:
        return False


def collect(config):
    checks = []

    def check(name, operation):
        try:
            result = operation()
            checks.append({"name": name, "ok": bool(result), "detail": "passed" if result else "unavailable"})
        except (Error, OSError, ValueError) as exc:
            checks.append({"name": name, "ok": False, "detail": str(exc)})

    check("architecture", lambda: platform.machine() == "x86_64")
    cpu = Path("/proc/cpuinfo").read_text()
    flags = set(
        next((line.split(":", 1)[1].split() for line in cpu.splitlines() if line.startswith("flags")), [])
    )
    check("x86-64-v2", lambda: {"cx16", "lahf_lm", "popcnt", "sse4_1", "sse4_2", "ssse3"} <= flags)
    check("CPU virtualization", lambda: bool({"vmx", "svm"} & flags))
    check("KVM API", kvm_available)
    check("UEFI", lambda: Path("/sys/firmware/efi").is_dir())
    check("Secure Boot", secure_boot)
    check(
        "TPM2",
        lambda: any(
            p.read_text().strip() == "2" for p in Path("/sys/class/tpm").glob("tpm*/tpm_version_major")
        ),
    )
    ram_kib = int(
        next(
            line.split()[1]
            for line in Path("/proc/meminfo").read_text().splitlines()
            if line.startswith("MemTotal:")
        )
    )
    check("physical RAM", lambda: ram_kib // 1024 >= config["minimum_ram_mib"])
    check("installer utilities", lambda: all(shutil.which(name) for name in INSTALL_TOOLS))
    devices = []
    for selected in config["disks"]:

        def disk_check(selected=selected):
            devices.append(observe_disk(selected, unused=True))
            return True

        check(f"disk {selected['role']}", disk_check)
    for nic in config["network"]["links"]:

        def nic_check(nic=nic):
            observed = json.loads(run(["ip", "--json", "link"]).stdout)
            return any(nic["mac"] == d.get("permaddr", d.get("address")) for d in observed)

        check(f"NIC {nic['name']}", nic_check)
    firmware = run(["fwupdmgr", "get-devices", "--json"], check=False) if shutil.which("fwupdmgr") else None
    check("fwupd discovery", lambda: firmware is not None and firmware.returncode in (0, 2))
    return {
        "schema": 1,
        "ok": all(c["ok"] for c in checks),
        "checks": checks,
        "devices": devices,
        "physical_ram_mib": ram_kib // 1024,
        "firmware": json.loads(firmware.stdout) if firmware and firmware.returncode == 0 else None,
        "validation": "capability inventory; boot and firmware flashing still require commissioning",
    }


def partition_path(disk_path, number):
    matches = [n for n in walk(block_tree(disk_path)) if n.get("partn") == number]
    require(len(matches) == 1, f"cannot resolve partition {number} on {disk_path}")
    return matches[0]["name"]
