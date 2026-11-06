#!/usr/bin/python3
"""Fail a build on inherited desktop/security defaults, wrong origins, or missing host capabilities."""

import re
from pathlib import Path

from .common import read_json, require, run, write_json


def source_revision(directory):
    for file in Path("/usr/src/packages/SOURCES").glob("*.obsinfo"):
        values = dict(line.split(": ", 1) for line in file.read_text().splitlines() if ": " in line)
        if values.get("name") == "particleve":
            if "tree" in values:
                require(re.fullmatch(r"[0-9a-f]{40}", values["tree"]), "invalid staged source tree")
                return "particleve_tree", values["tree"]
            require(re.fullmatch(r"[0-9a-f]{40}", values.get("commit", "")), "invalid OBS source revision")
            return "particleve", values["commit"]
    result = run(["git", "-C", directory, "rev-parse", "HEAD"])
    require(re.fullmatch(r"[0-9a-f]{40}\n", result.stdout), "unresolved fork revision")
    return "particleve", result.stdout.strip()


FORBIDDEN = {
    "cockpit",
    "cockpit-machines",
    "libvirt-daemon",
    "NetworkManager",
    "PackageKit",
    "zram-generator-defaults",
    "gcc",
    "nodejs",
    "gdb",
    "gnome-shell",
    "plasma-workspace",
    "incus",
    "incus-client",
    "incus-agent",
}


def summary_check(summary):
    main = next(i for i in summary["Images"] if i["Image"] == "main")
    initrd = next(i for i in summary["Images"] if i["Image"] == "default-initrd")
    for image in (main, initrd, summary["Tools"]):
        require(
            image["Distribution"] == "fedora" and image["Release"] == "45",
            "Fedora 45 must be explicit in all trees",
        )
        require(
            any("systemd" in t["Source"] and t["Target"].endswith(".repo") for t in image["SandboxTrees"]),
            f"stable systemd repository missing from {image['Image']}",
        )
    require(main["Profiles"] == ["particleve"], "build only the ParticleVE profile")
    require(not (FORBIDDEN & set(main["Packages"])), "inherited desktop/build/zram package")
    require(
        not main["Credentials"] and not main["UnifiedKernelImageProfiles"],
        "demo credentials or recovery/reset UKIs present",
    )
    require(main["ImageId"] == "ParticleVE", "incorrect image identity")
    cmdline = main["KernelCommandLine"]
    require(
        "audit=1" in cmdline and "audit=0" not in cmdline and "zswap.enabled=1" in cmdline,
        "incorrect audit or zswap command line",
    )
    require(not any("ParticleOS_" in word for word in cmdline), "upstream OS discovery still inherited")
    require(
        main["MicrocodeHost"] is False
        and main["KernelModulesIncludeHost"] is False
        and main["KernelModulesInitrdIncludeHost"] is False,
        "build-host hardware pruning is enabled",
    )
    require(
        main["KernelModules"] == ["/.*/"]
        and {
            "default",
            "/drivers/scsi",
            "/drivers/nvme",
            "/drivers/md",
            "/drivers/char/tpm",
            "/drivers/net/ethernet",
        }
        <= set(main["KernelInitrdModules"]),
        "retain generic kernel and initrd module coverage",
    )
    require(
        {
            "systemd-container",
            "systemd-udev",
            "systemd-pam",
            "fwupd",
            "fwupd-efi",
            "udisks2",
            "mdadm",
            "btrfs-progs",
            "systemd",
            "qemu-kvm-core",
            "qemu-img",
            "edk2-ovmf",
        }
        <= set(main["Packages"]),
        "missing host runtime package",
    )


def root_check(root, *, tree="usr", output=None):
    query = "%{NAME}|%{EVR}|%{VENDOR}|%{DISTURL}\n"
    rows = [
        line.split("|", 3) for line in run(["rpm", "--root", root, "-qa", "--qf", query]).stdout.splitlines()
    ]
    names = {r[0] for r in rows}
    family = [r for r in rows if r[0].startswith("systemd") or r[0] in ("udev", "libudev")]
    require(
        family and all("system:systemd:stable" in row[3] for row in family),
        "systemd family contains packages outside upstream OBS stable",
    )
    require(len({row[1] for row in family}) == 1, "mixed systemd family versions")
    if tree != "tools":
        require(not (FORBIDDEN & names), "runtime contains a forbidden package")
    if tree == "usr":
        require(read_json(root / "usr/lib/particleve/build.json")["fedora"] == "45", "wrong base release")
        for path in (
            "usr/bin/particleve",
            "usr/bin/machinectl",
            "usr/bin/homectl",
            "usr/bin/userdbctl",
            "usr/bin/systemd-vmspawn",
            "usr/lib/systemd/systemd-sysupdate",
            "usr/lib/systemd/system/systemd-vmspawn@.service",
            "usr/share/zoneinfo/Europe/Berlin",
            "usr/libexec/particleve-homed-account",
        ):
            require((root / path).exists(), f"missing runtime artifact: {path}")
        require(
            "pam_systemd_home.so" in (root / "etc/authselect/system-auth").read_text(),
            "upstream PAM homed integration missing",
        )
        require(
            "particleve-homed-account" in (root / "etc/authselect/system-auth").read_text(),
            "homed account policy missing",
        )
        require(
            "particleve-homed-account" in (root / "usr/lib/pam.d/sshd").read_text(),
            "SSH must enforce the homed account policy independently of authselect's includes",
        )
        certificate = root / "usr/lib/particleve/trust/secure-boot.crt"
        helpers = list((root / "usr/libexec/fwupd/efi").glob("fwupdx64.efi*"))
        require(helpers, "fwupd EFI helper missing")
        signed = [p for p in helpers if p.name.endswith(".signed")]
        require(signed, "supply an OBS-built fwupd-efi package with the separately signed helper")
        for helper in signed:
            run(["sbverify", "--cert", certificate, helper])
        for path in ("etc/selinux/config", "usr/share/factory/etc/selinux/config"):
            require(
                "SELINUX=enforcing" in (root / path).read_text(),
                "SELinux factory configuration is not enforcing",
            )
        for path in (root / "etc/systemd/system").glob("*.wants/systemd-sysupdate*.timer"):
            require(not path.is_symlink(), f"uncommissioned timer enabled: {path}")
        require(not list((root / "usr/lib/sysupdate.d").glob("*.transfer")), "unguarded OS feed inherited")
        units = [p.name for p in (root / "usr/lib/systemd/system").glob("particleve-*") if p.is_file()]
        run(
            [
                "systemd-analyze",
                f"--root={root}",
                "--man=no",
                "verify",
                *units,
                "systemd-vmspawn@particleve-verify.service",
                "sshd.socket",
            ],
            timeout=120,
        )
    record = {
        "schema": 1,
        "tree": tree,
        "systemd": family,
        "persistent_state": {
            n: v
            for n, v, _, _ in rows
            if n in ("systemd", "systemd-container", "btrfs-progs", "libtpms", "kernel-core")
            or n.startswith(("qemu-", "edk2-", "swtpm"))
        },
        "packages": [
            {"name": n, "evr": v, "vendor": vendor, "origin": origin} for n, v, vendor, origin in rows
        ],
        "hardware_validation": "not performed by build checks",
    }
    if output:
        write_json(output, record)
    return record
