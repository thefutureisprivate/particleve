import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from particleve import config, resources
from particleve.common import Deferred, Error, digest
from tests.fixtures import host


class ResourceTests(unittest.TestCase):
    def test_optional_memory_reserve_uses_default_without_changing_installation_identity(self):
        settings = host()
        del settings["maintenance"]["minimum_available_ram_mib"]
        before = digest(settings)
        config.validate(settings)
        self.assertEqual(digest(settings), before)
        with patch.object(
            resources, "memory", return_value={"total_bytes": 4 * 1024**3, "available_bytes": 2 * 1024**3}
        ):
            report = resources.status(settings, [], healthy=True)
        self.assertEqual(report["memory"]["reserve_bytes"], 1024**3)

    def test_memory_reserve_does_not_count_swap(self):
        with patch.object(
            resources.Path,
            "read_text",
            return_value="MemTotal: 4194304 kB\nMemAvailable: 524288 kB\nSwapFree: 999999999 kB\n",
        ):
            ram = resources.memory()
        self.assertEqual(ram["available_bytes"], 512 * 1024**2)
        with (
            patch.object(resources, "memory", return_value=ram),
            patch.object(resources, "disk_health", side_effect=AssertionError("no disk query needed")),
            self.assertRaisesRegex(Deferred, "memory headroom"),
        ):
            resources.status(host(), [], healthy=True)

    def test_missing_kernel_availability_is_rejected(self):
        with (
            patch.object(resources.Path, "read_text", return_value="MemTotal: 4194304 kB\n"),
            self.assertRaises(Error),
        ):
            resources.memory()

    def test_smart_faults_and_missing_data_cannot_be_reported_as_passed(self):
        selected = host()["disks"][0]
        for code, report, expected in (
            (0, {"smart_status": {"passed": True}}, "passed"),
            (8, {"smart_status": {"passed": False}}, "attention"),
            (16, {"smart_status": {"passed": True}}, "attention"),
            (1, {"smartctl": {"messages": [{"string": "Unknown device type"}]}}, "unavailable"),
            (4, {"smart_status": {"passed": True}}, "unavailable"),
            (0, {}, "unavailable"),
        ):
            with (
                self.subTest(code=code, expected=expected),
                patch.object(resources, "observe_disk"),
                patch.object(
                    resources, "run", return_value=SimpleNamespace(returncode=code, stdout=json.dumps(report))
                ) as command,
            ):
                actual = resources.disk_health(selected)
                self.assertEqual(actual["status"], expected)
                self.assertEqual(command.call_args.args[0][-1], selected["path"])
                self.assertNotIn("--test", command.call_args.args[0])

    def test_disk_fault_defers_maintenance_but_unavailable_health_is_explicit(self):
        ram = {"total_bytes": 4 * 1024**3, "available_bytes": 2 * 1024**3}
        with (
            patch.object(resources, "memory", return_value=ram),
            patch.object(resources, "disk_health", return_value={"status": "attention"}),
            self.assertRaisesRegex(Deferred, "SMART health fault"),
        ):
            resources.status(host(), host()["disks"], healthy=True)
        with (
            patch.object(resources, "memory", return_value=ram),
            patch.object(resources, "disk_health", return_value={"status": "unavailable"}),
        ):
            report = resources.status(host(), host()["disks"], healthy=True)
        self.assertEqual([d["status"] for d in report["physical_disks"]], ["unavailable", "unavailable"])

    def test_missing_member_and_query_failure_remain_visible_in_degraded_status(self):
        with (
            patch.object(resources, "memory", return_value={"total_bytes": 4096, "available_bytes": 2048}),
            patch.object(resources, "disk_health", side_effect=Error("selected disk is absent")),
        ):
            report = resources.status(host(), host()["disks"], healthy=False)
        self.assertEqual(report["physical_disks"][0]["status"], "unavailable")
        self.assertIn("absent", report["physical_disks"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
