import tempfile
import unittest
from datetime import UTC, datetime

from particleve.common import Deferred, Error, lock
from particleve.coordinator import Coordinator, reboot_window
from tests.fixtures import Backend


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.backend = Backend()
        self.coordinator = Coordinator(self.temporary.name, self.backend)
        self.window = datetime(2026, 11, 6, 3, 30, tzinfo=UTC)

    def test_full_transaction_assessment_and_no_second_reboot(self):
        self.assertEqual(self.coordinator.prepare()["action"], "ready")
        self.assertNotIn("reboot", self.backend.calls)
        self.assertEqual(self.coordinator.reboot(now=self.window)["action"], "activation-requested")
        self.assertEqual(self.coordinator.reboot(now=self.window)["action"], "deferred")
        self.backend.current, self.backend.boot = "2", "second-boot"
        self.coordinator.assess()
        self.assertIsNone(self.coordinator.load()["pending"])
        self.assertEqual(self.coordinator.prepare()["reason"], "no newer OS release")
        self.assertEqual(self.backend.calls.count("reboot"), 1)

    def test_interruptions_at_every_resource_boundary_resume_same_version(self):
        boundaries = [
            "protect",
            "transfer-a",
            "transferred-a",
            "transfer-b",
            "transferred-b",
            "expose-a",
            "exposed-a",
            "expose-b",
            "exposed-b",
        ]
        for boundary in boundaries:
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as directory:
                backend = Backend()
                coordinator = Coordinator(directory, backend)
                backend.fail_at = boundary
                with self.assertRaises(OSError):
                    coordinator.prepare()
                self.assertNotIn("reboot", backend.calls)
                backend.latest, backend.fail_at = "3", None
                result = Coordinator(directory, backend).prepare()
                self.assertEqual(result, {"action": "ready", "version": "2"})
                self.assertEqual(backend.disks, {"a": "2", "b": "2"})

    def test_readiness_is_rechecked_against_actual_disk(self):
        self.coordinator.prepare()
        del self.backend.disks["b"]
        with self.assertRaises(Error):
            self.coordinator.reboot(now=self.window)
        self.assertNotIn("reboot", self.backend.calls)

    def test_firmware_missing_disk_schema_and_commissioning_block(self):
        for blocker in ("firmware", "disk", "schema"):
            with self.subTest(blocker=blocker):
                self.backend.blocked = blocker
                self.assertEqual(self.coordinator.prepare()["action"], "deferred")
                self.assertNotIn("transfer-a", self.backend.calls)
        self.backend.blocked = None
        self.backend.commissioned = False
        self.assertEqual(self.coordinator.prepare()["reason"], "not commissioned")

    def test_degradation_after_prepare_blocks_activation(self):
        self.coordinator.prepare()
        self.backend.blocked = "disk"
        self.assertEqual(self.coordinator.reboot(now=self.window)["action"], "deferred")
        self.assertNotIn("select", self.backend.calls)

    def test_maintenance_persists_and_serializes(self):
        self.coordinator.maintenance("supervised firmware")
        reopened = Coordinator(self.temporary.name, self.backend)
        self.assertIn("manual maintenance", reopened.prepare()["reason"])
        with self.assertRaises(Error):
            reopened.maintenance(reviewed=False)
        reopened.maintenance(reviewed=True)
        with lock(self.temporary.name), self.assertRaises(Deferred):
            reopened.prepare()

    def test_fallback_quarantines_before_old_daemon_is_started(self):
        self.coordinator.prepare()
        self.coordinator.reboot(now=self.window)
        self.backend.boot = "after-fallback"
        self.coordinator.runtime_guard()
        self.assertIn("2", self.coordinator.load()["rejected"])
        self.assertLess(self.backend.calls.index("reject-2"), self.backend.calls.index("daemon-state"))
        self.assertIn("quarantined", self.coordinator.prepare()["reason"])
        self.assertEqual(self.backend.calls.count("reboot"), 1)

    def test_no_boot_change_does_not_imply_fallback(self):
        self.coordinator.prepare()
        self.coordinator.reboot(now=self.window)
        self.coordinator.runtime_guard()
        self.assertNotIn("2", self.coordinator.load()["rejected"])

    def test_changed_release_cannot_resume(self):
        self.backend.fail_at = "transferred-a"
        with self.assertRaises(OSError):
            self.coordinator.prepare()
        self.backend.releases["2"]["artifacts"]["usr"]["sha256"] = "b" * 64
        self.backend.fail_at = None
        with self.assertRaises(Error):
            self.coordinator.prepare()

    def test_no_update_and_missed_window_do_not_reboot(self):
        self.backend.latest = "1"
        self.coordinator.prepare()
        self.assertEqual(self.coordinator.reboot(now=self.window)["action"], "deferred")
        self.backend.latest = "2"
        self.coordinator.prepare()
        daytime = datetime(2026, 11, 6, 9, 0, tzinfo=UTC)
        self.assertEqual(self.coordinator.reboot(now=daytime)["action"], "deferred")
        self.assertNotIn("reboot", self.backend.calls)
        self.assertNotIn("freeze-vms", self.backend.calls)

    def test_shutdown_failure_cancels_activation_and_restores_vms(self):
        self.coordinator.prepare()

        def refuse():
            raise Deferred("VM refused poweroff")

        self.backend.stop_vms = refuse
        result = self.coordinator.reboot(now=self.window)
        self.assertEqual(result["action"], "deferred")
        self.assertIn("restore-vms", self.backend.calls)
        self.assertNotIn("reboot", self.backend.calls)
        self.assertEqual(self.coordinator.load()["pending"]["phase"], "ready")

    def test_failed_reboot_queue_restores_the_running_set(self):
        self.coordinator.prepare()
        self.backend.conditional_reboot = lambda version: False
        with self.assertRaises(Error):
            self.coordinator.reboot(now=self.window)
        self.assertIn("restore-vms", self.backend.calls)
        self.assertEqual(self.coordinator.load()["pending"]["phase"], "ready")

    def test_both_dst_transitions_and_adjacent_minutes(self):
        for day, utc_hour in (("2026-03-29", 2), ("2026-10-25", 3)):
            self.assertTrue(reboot_window(datetime.fromisoformat(f"{day}T{utc_hour:02}:30:00+00:00")))
            for minute in (29, 31):
                self.assertFalse(
                    reboot_window(datetime.fromisoformat(f"{day}T{utc_hour:02}:{minute}:00+00:00"))
                )


if __name__ == "__main__":
    unittest.main()
