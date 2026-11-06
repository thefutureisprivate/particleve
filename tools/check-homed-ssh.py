#!/usr/bin/python3
"""Check cold-home key/PAM SSH using one disposable homed account on a booted ParticleVE host."""

import json
import os
import secrets
import tempfile
import time
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
    password = secrets.token_urlsafe(48)
    password_hash = run(["openssl", "passwd", "-6", "-stdin"], input=password).stdout.strip()
    identity = directory / "identity.json"
    identity.write_text(
        json.dumps(
            {
                "userName": username,
                "storage": "subvolume",
                "shell": "/bin/bash",
                "privileged": {
                    "hashedPassword": [password_hash],
                    "sshAuthorizedKeys": [key.with_suffix(".pub").read_text().strip()],
                },
                "secret": {"password": [password]},
            }
        )
    )
    identity.chmod(0o600)
    created = False
    try:
        run(["homectl", "--no-ask-password", "create", username, f"--identity={identity}"])
        created = True
        machine_id = Path("/etc/machine-id").read_text().strip()

        def home_state():
            record = json.loads(run(["homectl", "--json=short", "inspect", username]).stdout)
            return record.get("status", {}).get(machine_id, {}).get("state")

        if home_state() == "active":
            run(["homectl", "deactivate", username])
        require(home_state() == "inactive", "SSH acceptance check requires an inactive home")
        run(["getent", "passwd", username])
        public_key = key.with_suffix(".pub").read_text().split()[:2]
        keys = run(["userdbctl", "ssh-authorized-keys", username]).stdout.splitlines()
        require(
            any(line.split()[:2] == public_key for line in keys),
            "upstream userdb did not return the inactive user's SSH key",
        )
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
        require(run(command, timeout=45, check=False).returncode != 0, "SSH key alone bypassed PAM")
        require(home_state() == "inactive", "key-only attempt unexpectedly activated the home")
        password_file = directory / "password"
        password_file.write_text(password)
        password_file.chmod(0o600)
        askpass = directory / "askpass"
        askpass.write_text(f"#!/bin/sh\nexec /usr/bin/cat '{password_file}'\n")
        askpass.chmod(0o700)
        os.environ.update(
            SSH_ASKPASS=str(askpass), SSH_ASKPASS_REQUIRE="force", DISPLAY="particleve-acceptance"
        )
        command[command.index("BatchMode=yes")] = "BatchMode=no"
        result = run(command, input="", timeout=45)
        require(result.stdout.strip() == username, "SSH did not enter the expected homed account")
        record = json.loads(
            run(
                ["userdbctl", "--service=io.systemd.Home", "--with-nss=no", "--output=json", "user", username]
            ).stdout
        )
        require(record["storage"] == "subvolume", "test account did not use subvolume storage")
    finally:
        if created:
            run(["loginctl", "terminate-user", username], check=False)
            deadline = time.monotonic() + 30
            while home_state() != "inactive" and time.monotonic() < deadline:
                if home_state() == "active":
                    run(["homectl", "deactivate", username], check=False, timeout=120)
                time.sleep(1)
            require(home_state() == "inactive", "disposable home did not become inactive for cleanup")
            run(["homectl", "remove", username], timeout=120)
print(json.dumps({"cold_home_ssh": "pass", "image": image_version(), "disposable_user": username}))
