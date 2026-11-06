import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from particleve import install
from particleve.common import Error, read_json


class TPMEnrollmentTests(unittest.TestCase):
    def test_replacement_crypttab_tracks_new_luks_identity_and_preserves_peer_swap(self):
        manifest = self.backend(Path("/unused")).manifest
        manifest["devices"][0]["state_luks_uuid"] = "replacement-a"
        text = install.crypttab(manifest)
        self.assertIn("particleve-state-a UUID=replacement-a - ", text)
        self.assertIn("particleve-state-b UUID=state-b - ", text)
        self.assertIn("particleve-swap UUID=swap - tpm2-device=auto\n", text)
        self.assertNotIn("UUID=state-a ", text)

    def test_replacement_copy_stays_owned_until_completion_without_short_timeout(self):
        with patch.object(install, "run") as command:
            install.replace_btrfs(1, "/dev/mapper/particleve-state-a")
        self.assertEqual(
            command.call_args.args[0],
            ["btrfs", "replace", "start", "-B", "1", "/dev/mapper/particleve-state-a", "/"],
        )
        self.assertIsNone(command.call_args.kwargs["timeout"])

    def test_recovery_installer_formats_without_binding_its_pcr7(self):
        with patch.object(install, "run", return_value=SimpleNamespace(stdout="test-uuid\n")) as commands:
            install.format_encrypted("/dev/disposable", "test", "/run/test-key", enroll=False)
        self.assertEqual([c.args[0][0] for c in commands.call_args_list], ["cryptsetup"] * 3)

    def backend(self, directory):
        manifest = {
            "devices": [
                {"role": "a", "state_luks_uuid": "state-a"},
                {"role": "b", "state_luks_uuid": "state-b"},
            ],
            "swap": {"luks_uuid": "swap"},
        }
        calls = []
        return SimpleNamespace(
            directory=directory,
            config={"tpm_policy": "pcr7+signed-pcr11"},
            manifest=manifest,
            current_version=lambda: "1",
            boot_id=lambda: "normal-boot",
            check_storage=lambda **kwargs: calls.append("storage"),
            check_firmware_clear=lambda: calls.append("firmware"),
            release=lambda version: {"version": version},
            verify_disk=lambda *args, **kwargs: True,
        )

    def test_only_verified_normal_boot_enrolls_all_three_and_preserves_slots(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            backend = self.backend(directory)
            with (
                patch.object(install, "validate_keyfile"),
                patch.object(install.inventory, "secure_boot", return_value=True),
                patch.object(install.inventory, "measured_boot", return_value=True),
                patch.object(install, "member", side_effect=lambda d, role: "/dev/test-" + d["role"]),
                patch.object(install, "run", return_value=SimpleNamespace(stdout="")) as commands,
            ):
                install.enroll_tpm(backend, "/run/test-key", {"pending": None, "maintenance": None})
            self.assertEqual(len(commands.call_args_list), 3)
            for call in commands.call_args_list:
                self.assertIn("--tpm2-pcrs=7", call.args[0])
                self.assertIn("--tpm2-public-key-pcrs=11", call.args[0])
                self.assertFalse(any("wipe-slot" in str(a) for a in call.args[0]))
            record = read_json(directory / "tpm-enrollment.json")
            self.assertEqual(record["boot_id"], "normal-boot")
            self.assertEqual(record["luks_uuids"], ["state-a", "state-b", "swap"])

    def test_unmeasured_boot_cannot_enroll_a_volume(self):
        with (
            patch.object(install.inventory, "measured_boot", side_effect=Error("unmeasured boot")),
            patch.object(install, "run") as commands,
            self.assertRaisesRegex(Error, "unmeasured boot"),
        ):
            install.enroll_source("/dev/disposable", "/run/test-key")
        commands.assert_not_called()

    def test_interruption_never_records_completion_and_can_be_retried(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            backend = self.backend(directory)
            with (
                patch.object(install, "validate_keyfile"),
                patch.object(install.inventory, "secure_boot", return_value=True),
                patch.object(install, "member", side_effect=lambda d, role: "/dev/test-" + d["role"]),
                patch.object(install, "enroll_source", side_effect=[None, Error("interrupted")]),
                self.assertRaises(Error),
            ):
                install.enroll_tpm(backend, "/run/test-key", {"pending": None, "maintenance": None})
            self.assertFalse((directory / "tpm-enrollment.json").exists())
            with (
                patch.object(install, "validate_keyfile"),
                patch.object(install.inventory, "secure_boot", return_value=True),
                patch.object(install, "member", side_effect=lambda d, role: "/dev/test-" + d["role"]),
                patch.object(install, "enroll_source"),
            ):
                install.enroll_tpm(backend, "/run/test-key", {"pending": None, "maintenance": None})
            self.assertTrue((directory / "tpm-enrollment.json").exists())

    def test_pending_update_or_commissioned_host_without_maintenance_cannot_enroll(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            backend = self.backend(directory)
            for pending, commissioned in (({"version": "2"}, False), (None, True)):
                if commissioned:
                    (directory / "commissioned.json").write_text("{}")
                with (
                    patch.object(install, "validate_keyfile"),
                    patch.object(install, "enroll_source") as enroll,
                ):
                    with self.assertRaises(Error):
                        install.enroll_tpm(
                            backend, "/run/test-key", {"pending": pending, "maintenance": None}
                        )
                    enroll.assert_not_called()


if __name__ == "__main__":
    unittest.main()
