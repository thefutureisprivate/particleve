"""Finalize the native OBS signing pipeline and describe only verified final artifacts."""

import base64
import json
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path

from .common import atomic_write, hash_file, read_json, require, run, write_json
from .config import VERSION
from .release import inspect_uki, validate


def assemble(artifacts, version, root_hash, bootloader, fwupd_efi, verification, sources, output):
    """Build one manifest, after all deferred signatures have been attached."""
    require(VERSION.fullmatch(version), "invalid image version")
    require(verification["tree"] == "usr" and verification["systemd"], "missing image verification")
    counters = [int(x) for x in version.split(".")]
    sequence = counters[0] * 1_000_000 + (counters[1] if len(counters) == 2 else 0)
    manifest = {
        "schema": 1,
        "version": version,
        "sequence": sequence,
        "architecture": "x86-64",
        "cpu_baseline": "x86-64-v2",
        "fedora": "45",
        "persistent_state": verification["persistent_state"],
        "usr_root_hash": root_hash,
        "sources": sources,
        "packages": verification["packages"],
        "artifacts": {},
    }
    for kind, suffix in (
        ("usr", "usr-x86-64"),
        ("verity", "usr-x86-64-verity"),
        ("verity_sig", "usr-x86-64-verity-sig"),
    ):
        files = list(artifacts.glob(f"ParticleVE_{version}_x86-64.{suffix}.*.raw"))
        require(len(files) == 1, f"missing/ambiguous final {kind} artifact")
        source = files[0]
        manifest["artifacts"][kind] = {
            "file": source.name,
            "size": source.stat().st_size,
            "sha256": hash_file(source),
            "partition_uuid": str(uuid.UUID(source.name.split(".")[-2])),
        }
        if source.parent != output:
            shutil.copy2(source, output / source.name)
    uki = artifacts / f"ParticleVE_{version}_x86-64.efi"
    for kind, source, name in (
        ("uki", uki, uki.name),
        ("bootloader", bootloader, f"ParticleVE_{version}_x86-64.systemd-bootx64.efi"),
        ("fwupd_efi", fwupd_efi, f"ParticleVE_{version}_x86-64.fwupdx64.efi.signed"),
    ):
        manifest["artifacts"][kind] = {
            "file": name,
            "size": source.stat().st_size,
            "sha256": hash_file(source),
        }
        if source != output / name:
            shutil.copy2(source, output / name)
    validate(manifest)
    return manifest


def carry_signing_hook(output):
    """OBS rebuilds each signing stage from its generated minimal mkosi.conf."""
    config = output / "mkosi.conf"
    require(config.is_file(), "OBS signing stage is missing its continuation recipe")
    # Format=none continuations return before postoutput scripts.
    hook = "BuildScripts=/usr/libexec/particleve-obs-postoutput"
    if hook not in config.read_text():
        with config.open("a") as stream:
            stream.write("\n[Content]\n" + hook + "\n\n[Output]\nCompressOutput=no\n")


def postoutput():
    output = Path(os.environ.get("OUTPUTDIR", "/work/src/usr/src/packages/OTHER"))
    if (output / "hashes.cpio.rsasign").exists():
        carry_signing_hook(output)
        return
    # A final stage is complete only after mkosi-obs has attached PCR, PE and verity signatures.
    ukis = list(output.glob("ParticleVE_*_x86-64.efi"))
    require(len(ukis) == 1, "final signing stage must contain exactly one ParticleVE UKI")
    match = re.fullmatch(r"ParticleVE_([0-9.]+)_x86-64.efi", ukis[0].name)
    require(match, "invalid final image identity")
    version = match[1]
    usr = list(output.glob(f"ParticleVE_{version}_x86-64.usr-x86-64.*.raw"))
    signatures = list(output.glob(f"ParticleVE_{version}_x86-64.usr-x86-64-verity-sig.*.raw"))
    require(len(usr) == len(signatures) == 1, "final signed partition artifacts missing")
    with tempfile.TemporaryDirectory(prefix="particleve-final-") as temporary:
        work = Path(temporary)
        root = work / "usr"
        run(["fsck.erofs", f"--extract={root}", usr[0]], timeout=600)
        verification = read_json(root / "lib/particleve/verification.json")
        build = read_json(root / "lib/particleve/build.json")
        certificate = root / "lib/particleve/trust/secure-boot.crt"
        actual_cert = Path("/usr/src/packages/SOURCES/_projectcert.crt")
        for cert in (certificate, actual_cert):
            require(cert.is_file(), "missing project certificate")
        require(
            run(["openssl", "x509", "-in", certificate, "-outform", "PEM"]).stdout
            == run(["openssl", "x509", "-in", actual_cert, "-outform", "PEM"]).stdout,
            "image trust does not match the OBS signing project",
        )
        signature = json.loads(signatures[0].read_bytes().rstrip(b"\0"))
        root_hash = signature["rootHash"]
        require(re.fullmatch(r"[0-9a-f]{64}", root_hash), "invalid signed verity root hash")
        (work / "roothash").write_text(root_hash)
        (work / "roothash.p7s").write_bytes(base64.b64decode(signature["signature"], validate=True))
        run(
            [
                "openssl",
                "smime",
                "-verify",
                "-inform",
                "DER",
                "-in",
                work / "roothash.p7s",
                "-content",
                work / "roothash",
                "-nointern",
                "-certfile",
                certificate,
                "-noverify",
            ]
        )
        disk = output / f"ParticleVE_{version}_x86-64.raw"
        partitions = json.loads(run(["systemd-repart", "--json=short", disk]).stdout)
        esps = [part for part in partitions if part["type"] == "esp"]
        require(len(esps) == 1, "final DDI lacks an unambiguous ESP")
        bootloader = work / "systemd-bootx64.efi"
        run(["mcopy", "-i", f"{disk}@@{esps[0]['offset']}", "::EFI/systemd/systemd-bootx64.efi", bootloader])
        helper = root / "libexec/fwupd/efi/fwupdx64.efi.signed"
        manifest = assemble(
            output, version, root_hash, bootloader, helper, verification, build["sources"], output
        )
        for kind in ("uki", "bootloader", "fwupd_efi"):
            run(["sbverify", "--cert", certificate, output / manifest["artifacts"][kind]["file"]])
        inspect_uki(ukis[0], manifest)
        run(
            ["veritysetup", "verify", usr[0], output / manifest["artifacts"]["verity"]["file"], root_hash],
            timeout=600,
        )
        write_json(output / f"ParticleVE_{version}_x86-64.release.json", manifest)
        # Intermediate mkosi checksums precede final signatures. OBS publishes its own signed index.
        for file in output.glob("*.sha256"):
            file.unlink()
        atomic_write(output / "particleve-build-verified", (version + "\n").encode(), 0o644)
