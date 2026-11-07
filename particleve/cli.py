"""The public command line. Mutating host operations require root."""

import argparse
import json
import os
import sys
from pathlib import Path

from . import commission, config, install, inventory, network, reconfigure, release
from .common import Error, atomic_write, digest, lock, read_json, require, run, write_json
from .coordinator import Coordinator
from .linux import Linux


def parser():
    p = argparse.ArgumentParser(description="ParticleVE installation and serialized host maintenance")
    p.add_argument("--config", default="/etc/particleve/host.json")
    p.add_argument("--state-dir", default="/var/lib/particleve")
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("preflight", help="read-only hardware capability report")
    commands.add_parser("apply-firewall", help="apply this image's host-input policy to the configured host")
    render = commands.add_parser("render-network")
    render.add_argument("--output", required=True, help="staging directory, never activated automatically")
    fetching = commands.add_parser("fetch-release", help="download and authenticate a complete OS release")
    fetching.add_argument("--output", required=True, help="release cache directory")
    fetching.add_argument("--version", help="specific published version; otherwise select the newest")
    fetching.add_argument("--keyring", default="/usr/lib/particleve/trust/releases.gpg")
    fetching.add_argument("--certificate", default="/usr/lib/particleve/trust/secure-boot.crt")
    for name in ("plan", "install"):
        sub = commands.add_parser(name)
        sub.add_argument("--release-dir", required=True)
        sub.add_argument("--keyring", default="/usr/lib/particleve/trust/releases.gpg")
        sub.add_argument("--certificate", default="/usr/lib/particleve/trust/secure-boot.crt")
        if name == "plan":
            sub.add_argument("--output", required=True)
        else:
            sub.add_argument("--plan", required=True)
            sub.add_argument("--confirm", required=True, help="SHA256 of the reviewed disk-erasing plan")
            sub.add_argument("--recovery-key-file", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument(
        "--manual",
        action="store_true",
        help="allow preparation before commissioning; all safety guards still apply",
    )
    activation = commands.add_parser("activate")
    activation.add_argument(
        "--manual",
        action="store_true",
        help="activate now before commissioning; retain disk, firmware and graceful VM shutdown guards",
    )
    enrollment = commands.add_parser(
        "enroll-tpm", help="enroll from the verified normal boot, preserving recovery slots"
    )
    enrollment.add_argument("--recovery-key-file", required=True)
    for name in (
        "assess",
        "bless-current",
        "runtime-guard",
        "recover-vms",
        "finalize-replacement",
        "check-users",
        "fail-boot",
        "status",
        "disable-automation",
    ):
        commands.add_parser(name)
    maintenance = commands.add_parser("maintenance")
    maintenance.add_argument("action", choices=("enter", "leave"))
    maintenance.add_argument("--reason")
    maintenance.add_argument("--reviewed", action="store_true")
    commissioning = commands.add_parser("commission")
    commissioning.add_argument("--evidence", required=True)
    commissioning.add_argument("--enable", action="store_true")
    settings = commands.add_parser("reconfigure", help="review and rebind operational policy in maintenance")
    settings.add_argument("--previous-config", required=True, help="the previously bound configuration")
    settings.add_argument("--proposed", required=True, help="the proposed validated policy")
    settings.add_argument("--confirm", help="SHA256 of the reviewed reconfiguration plan")
    replacement = commands.add_parser("replace-disk")
    replacement.add_argument("--role", choices=("a", "b"), required=True)
    replacement.add_argument("--disk", required=True)
    replacement.add_argument("--serial", required=True)
    replacement.add_argument("--confirm")
    replacement.add_argument("--recovery-key-file")
    return p


def execute(args):
    if args.command == "disable-automation":
        require(os.geteuid() == 0, "host maintenance commands require root")
        print(json.dumps(reconfigure.disable_automation(args.state_dir), indent=2))
        return 0
    if args.command == "reconfigure":
        require(os.geteuid() == 0, "host maintenance commands require root")
        result = reconfigure.reconfigure(
            args.state_dir,
            args.config,
            read_json(args.previous_config),
            read_json(args.proposed),
            confirmation=args.confirm,
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "status":
        result = reconfigure.binding_status(args.config, args.state_dir)
        if not result["config_binding"]["valid"] or result["reconfiguration_pending"]:
            print(json.dumps(result, indent=2))
            return 0
    host = config.validate(
        read_json(args.config), publication=args.command not in ("preflight", "render-network")
    )
    if args.command == "preflight":
        report = inventory.collect(host)
        print(json.dumps(report, indent=2))
        return 0 if report["ok"] else 1
    if args.command == "render-network":
        network.write(host, args.output)
        atomic_write(Path(args.output) / "host.nft", network.firewall(host).encode(), 0o644)
        result = {"output": str(Path(args.output).resolve())}
    elif args.command == "apply-firewall":
        require(os.geteuid() == 0, "applying the host firewall requires root")
        run(["nft", "--file", "-"], input=network.firewall(host))
        result = {"firewall": "active"}
    elif args.command == "fetch-release":
        destination, manifest = release.fetch(
            host["feed"], args.output, args.keyring, args.certificate, version=args.version
        )
        result = {"release_dir": str(destination.resolve()), "version": manifest["version"]}
    elif args.command == "plan":
        manifest = release.verify_directory(args.release_dir, args.keyring, args.certificate)
        proposed = install.plan(host, manifest)
        write_json(args.output, proposed)
        result = {"plan": str(Path(args.output).resolve()), "confirmation": proposed["confirmation"]}
    elif args.command == "install":
        result = install.install(
            host,
            args.release_dir,
            read_json(args.plan),
            args.confirm,
            args.recovery_key_file,
            keyring=args.keyring,
            certificate=args.certificate,
        )
    else:
        if args.command != "status":
            require(os.geteuid() == 0, "host maintenance commands require root")
        backend = Linux(
            host, args.state_dir, allow_unbound=args.command == "maintenance" and args.action == "enter"
        )
        coordinator = Coordinator(args.state_dir, backend)
        if args.command == "prepare":
            result = coordinator.prepare(automatic=not args.manual)
        elif args.command == "enroll-tpm":
            with lock(args.state_dir):
                result = install.enroll_tpm(backend, args.recovery_key_file, coordinator.load())
        elif args.command == "activate":
            result = coordinator.reboot(automatic=not args.manual)
        elif args.command == "assess":
            result = coordinator.assess()
        elif args.command == "bless-current":
            result = coordinator.bless()
        elif args.command == "runtime-guard":
            backend.check_storage(healthy=False)
            coordinator.runtime_guard()
            result = {"runtime_state": "compatible"}
        elif args.command == "maintenance":
            require(args.action != "enter" or args.reason, "maintenance enter requires --reason")
            result = coordinator.maintenance(
                args.reason if args.action == "enter" else None, reviewed=args.reviewed
            )
        elif args.command == "commission":
            with lock(args.state_dir):
                result = commission.commission(backend, args.evidence, enable=args.enable)
        elif args.command == "recover-vms":
            with lock(args.state_dir):
                result = backend.recover_vms()
        elif args.command == "finalize-replacement":
            with lock(args.state_dir):
                result = install.finalize_replacement(backend)
        elif args.command == "check-users":
            from .accounts import check

            result = check()
        elif args.command == "fail-boot":
            with lock(args.state_dir):
                state = coordinator.load()
                pending = state["pending"]
                if all(
                    run(["systemctl", "is-active", "--quiet", unit], check=False).returncode == 0
                    for unit in ("boot-complete.target", "systemd-bless-boot.service")
                ):
                    result = {"boot": "already complete"}
                elif pending and pending["version"] == backend.current_version():
                    pending["phase"] = "booting"
                    pending["boot_id"] = backend.boot_id()
                    coordinator.save(state)
                    run(["systemctl", "--no-block", "reboot"])
                    result = {"failed_candidate": "retry/fallback requested through boot counting"}
                else:
                    run(["systemctl", "--no-block", "isolate", "emergency.target"])
                    result = {"boot_failure": "owner recovery required"}
        elif args.command == "replace-disk":
            with lock(args.state_dir):
                result = install.replace(
                    host,
                    backend,
                    args.role,
                    {"role": args.role, "path": args.disk, "serial": args.serial},
                    confirmation=args.confirm,
                    keyfile=args.recovery_key_file,
                )
        else:
            result = {
                "state": coordinator.load(),
                "installation_sha256": digest(backend.manifest),
                "capacity": backend.check_storage(healthy=False),
                "resources": backend.check_resources(healthy=False),
                "commissioned": (backend.directory / "commissioned.json").exists(),
            }
    print(json.dumps(result, indent=2))
    return 0


def main():
    args = parser().parse_args()
    try:
        return execute(args)
    except (Error, OSError, KeyError, ValueError, TypeError, StopIteration) as exc:
        print(f"particleve: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
