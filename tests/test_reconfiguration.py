import copy
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from particleve import cli, reconfigure
from particleve.common import Error, digest, read_json, write_json
from particleve.linux import Linux
from tests.fixtures import host


class ReconfigurationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.config_file = self.directory / "host.json"
        self.previous = host()
        self.proposed = copy.deepcopy(self.previous)
        self.proposed["maintenance"]["minimum_available_ram_mib"] = 1280
        self.manifest = {"schema": 1, "config_sha256": digest(self.previous), "devices": ["unchanged"]}
        write_json(self.directory / "installation.json", self.manifest)
        write_json(
            self.directory / "state.json", {"schema": 1, "maintenance": {"reason": "policy"}, "pending": None}
        )
        write_json(self.directory / "commissioned.json", {"old": "approval"})
        write_json(self.config_file, self.previous)

    def preview(self):
        return reconfigure.reconfigure(self.directory, self.config_file, self.previous, self.proposed)

    def apply(self, confirmation):
        return reconfigure.reconfigure(
            self.directory, self.config_file, self.previous, self.proposed, confirmation=confirmation
        )

    def test_reviewed_policy_rebinds_and_can_initialize_for_recommissioning(self):
        plan = self.preview()
        self.assertTrue((self.directory / "commissioned.json").exists())
        with patch("particleve.reconfigure.run") as commands:
            result = self.apply(plan["confirmation"])
        self.assertEqual(result["action"], "reconfigured")
        self.assertEqual(commands.call_count, 1)
        self.assertEqual(read_json(self.config_file), self.proposed)
        self.assertFalse((self.directory / "commissioned.json").exists())
        self.assertFalse((self.directory / "reconfiguration.json").exists())
        backend = Linux(self.proposed, self.directory)
        self.assertEqual(backend.manifest, {**self.manifest, "config_sha256": digest(self.proposed)})
        self.assertTrue(read_json(self.directory / "state.json")["maintenance"])

    def test_interrupted_pair_of_writes_resumes_only_the_exact_reviewed_operation(self):
        plan = self.preview()
        actual_write = write_json

        def fail_manifest(path, value):
            if Path(path).name == "installation.json":
                raise OSError("disposable interruption after writing configuration")
            actual_write(path, value)

        with (
            patch("particleve.reconfigure.run"),
            patch("particleve.reconfigure.write_json", side_effect=fail_manifest),
            self.assertRaises(OSError),
        ):
            self.apply(plan["confirmation"])
        self.assertFalse((self.directory / "commissioned.json").exists())
        with self.assertRaisesRegex(Error, "reconfiguration interrupted"):
            Linux(self.proposed, self.directory)
        self.assertTrue(self.preview()["resume"])
        with patch("particleve.reconfigure.run"):
            self.apply(plan["confirmation"])
        self.assertEqual(Linux(self.proposed, self.directory).config, self.proposed)

    def test_disk_or_layout_change_is_rejected_before_any_write_or_command(self):
        for path, value in ((["disks", 0, "serial"], "another"), (["storage", "esp_mib"], 4096)):
            candidate = copy.deepcopy(self.proposed)
            target = candidate
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            with (
                self.subTest(path=path),
                patch("particleve.reconfigure.write_json") as writes,
                patch("particleve.reconfigure.run") as commands,
                self.assertRaisesRegex(Error, "operational policy"),
            ):
                reconfigure.reconfigure(
                    self.directory, self.config_file, self.previous, candidate, confirmation="bad"
                )
            writes.assert_not_called()
            commands.assert_not_called()

    def test_status_and_disable_do_not_need_a_valid_configuration_binding(self):
        write_json(self.config_file, self.proposed)
        args = cli.parser().parse_args(
            ["--config", str(self.config_file), "--state-dir", str(self.directory), "status"]
        )
        with redirect_stdout(io.StringIO()) as output, patch("particleve.cli.Linux") as backend:
            self.assertEqual(cli.execute(args), 0)
        self.assertIn('"valid": false', output.getvalue())
        backend.assert_not_called()
        self.config_file.write_text("invalid JSON")
        args.command = "disable-automation"
        with (
            patch("particleve.cli.os.geteuid", return_value=0),
            patch("particleve.reconfigure.run") as commands,
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(cli.execute(args), 0)
        self.assertEqual(commands.call_count, 1)
        self.assertFalse((self.directory / "commissioned.json").exists())

    def test_invalid_json_still_has_a_diagnostic_status(self):
        self.config_file.write_text("invalid JSON")
        status = reconfigure.binding_status(self.config_file, self.directory)
        self.assertFalse(status["config_binding"]["valid"])
