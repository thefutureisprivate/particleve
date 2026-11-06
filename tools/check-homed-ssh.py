#!/usr/bin/python3
"""Check cold-home public-key SSH using one disposable homed account on a booted ParticleVE host."""

import json
import os
import secrets
import tempfile
from pathlib import Path

from particleve.common import require, run
from particleve.linux import image_version

require(os.geteuid() == 0, "run this acceptance check as root on the target ParticleVE host")
image_version()  # Do not modify a developer workstation's account database.
username = "pvssh" + secrets.token_hex(4)
with tempfile.TemporaryDirectory(prefix="particleve-ssh-", dir="/run") as temporary:
    directory = Path(temporary)
    key = directory / "id_ed25519"
    run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", key])
    password_hash = run(["openssl", "passwd", "-6", "-stdin"], input=secrets.token_urlsafe(48)).stdout.strip()
    identity = directory / "identity.json"
    identity.write_text(
        json.dumps(
            {
                "userName": username,
                "storage": "subvolume",
                "shell": "/bin/bash",
                "sshAuthorizedKeys": [key.with_suffix(".pub").read_text().strip()],
                "privileged": {"hashedPassword": [password_hash]},
            }
        )
    )
    identity.chmod(0o600)
    created = False
    try:
        run(["homectl", "create", username, f"--identity={identity}"])
        created = True
        run(["homectl", "deactivate", username])
        # Bind this local test to the installed server key; do not disable host-key verification.
        public = Path("/etc/ssh/ssh_host_ed25519_key.pub").read_text().strip()
        known = directory / "known_hosts"
        known.write_text("127.0.0.1 " + public + "\n")
        command = [
            "ssh",
            "-i",
            str(key),
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            f"UserKnownHostsFile={known}",
            username + "@127.0.0.1",
            'id -un; test -w "$HOME" && touch "$HOME/.particleve-ssh-test"',
        ]
        result = run(command, timeout=45)
        require(result.stdout.strip() == username, "SSH did not enter the expected homed account")
        record = json.loads(
            run(
                ["userdbctl", "--service=io.systemd.Home", "--with-nss=no", "--output=json", "user", username]
            ).stdout
        )
        require(record["storage"] == "subvolume", "test account did not use subvolume storage")
        print(json.dumps({"cold_home_ssh": "pass", "image": image_version(), "disposable_user": username}))
    finally:
        if created:
            run(["loginctl", "terminate-user", username], check=False)
            run(["homectl", "remove", username], timeout=120)
