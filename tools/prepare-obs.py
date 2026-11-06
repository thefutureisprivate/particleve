#!/usr/bin/python3
"""Prepare native OBS sources from an exact reviewed Git tree, without signing or publishing it."""

import argparse
import io
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from particleve.common import atomic_write, require, run

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--tree", required=True, help="exact Git commit or tree object")
p.add_argument("--output", type=Path, default=Path("build/obs-packages"))
args = p.parse_args()
tree = run(["git", "rev-parse", f"{args.tree}^{{tree}}"]).stdout.strip()
archive = subprocess.run(["git", "archive", "--format=tar", tree], capture_output=True, check=True).stdout
image = args.output / "particleve-image"
integration = args.output / "particleve-integration"
for directory in (image, integration):
    require(not directory.exists(), f"output must be fresh: {directory}")
    directory.mkdir(parents=True)
with tarfile.open(fileobj=io.BytesIO(archive)) as source:
    for name, destination in (
        (".obs/fedora/x86-64/mkosi.conf", image / "mkosi.conf"),
        ("packaging/particleve-integration.spec", integration / "particleve-integration.spec"),
    ):
        atomic_write(destination, source.extractfile(name).read(), 0o644)
    with tarfile.open(integration / "particleve-integration-0.1.0.tar.xz", "w:xz") as output:
        for member in source.getmembers():
            content = source.extractfile(member) if member.isfile() else None
            member.name = "particleve-integration-0.1.0/" + member.name
            output.addfile(member, content)
with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    root = directory / "particleve"
    root.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        for member in source.getmembers():
            relative = Path(member.name)
            require(not relative.is_absolute() and ".." not in relative.parts, "unsafe source archive")
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if member.isdir():
                target.mkdir(exist_ok=True)
            elif member.issym():
                target.symlink_to(member.linkname)
            else:
                require(member.isfile(), "unexpected Git archive entry")
                with source.extractfile(member) as content, target.open("wb") as output:
                    shutil.copyfileobj(content, output)
                target.chmod(0o755 if member.mode & 0o111 else 0o644)
    paths = sorted(("particleve", *(str(path.relative_to(directory)) for path in root.rglob("*"))))
    with (image / "particleve.obscpio").open("wb") as output:
        subprocess.run(
            ["cpio", "--create", "--format=newc", "--null", "--quiet", "--reproducible"],
            input=b"\0".join(os.fsencode(path) for path in paths) + b"\0",
            cwd=directory,
            stdout=output,
            check=True,
        )
atomic_write(image / "particleve.obsinfo", f"name: particleve\ntree: {tree}\n".encode(), 0o644)
print(f"Prepared exact Git tree {tree}; automatic obs_scm will use main after the branch is published.")
