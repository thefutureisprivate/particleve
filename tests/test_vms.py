import copy
import tempfile
import unittest

from particleve.common import Deferred, Error, read_json
from particleve.vms import Shutdown


class Platform:
    def __init__(self):
        self.now = 0
        self.inhibited = False
        self.running = [
            {
                "unit": f"systemd-vmspawn@{name}.service",
                "machine": name,
                "processes": [{"pid": n, "starttime": 1}],
                "invocation": "original",
            }
            for name, n in (("a", 100), ("b", 200))
        ]
        self.exits = {}
        self.delays = {e["unit"]: 0 for e in self.running}
        self.started = []
        self.poweroffs = []
        self.replacement = set()
        self.fail_inventory = False
        self.fail_start = set()
        self.normal = True

    def clock(self):
        return self.now

    def pause(self, seconds):
        self.now += seconds

    def inhibit(self):
        self.inhibited = True

    def release(self):
        self.inhibited = False

    def jobs(self):
        return []

    def inventory(self):
        if self.fail_inventory:
            raise Error("unregistered QEMU process")
        return copy.deepcopy(self.running)

    def poweroff(self, entry):
        unit = entry["unit"]
        self.poweroffs.append(unit)
        delay = self.delays[unit]
        self.exits[unit] = None if delay is None else self.now + delay

    def alive(self, entry):
        exit_time = self.exits.get(entry["unit"])
        original = exit_time is None or self.now < exit_time
        return original, entry["unit"] in self.replacement

    def empty(self):
        if any(any(self.alive(e)) for e in self.running):
            raise Error("VM process still alive")

    def start(self, entry):
        assert not self.inhibited
        if entry["unit"] in self.fail_start:
            raise Error("start failed")
        if entry["unit"] not in self.replacement:
            self.started.append(entry["unit"])
            self.replacement.add(entry["unit"])

    def normal_operation(self):
        return self.normal


class VMShutdownTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.platform = Platform()
        self.shutdown = Shutdown(
            self.directory.name, self.platform, "boot1", graceful_seconds=5, restore_seconds=5
        )

    def test_success_waits_for_process_exit_and_keeps_start_gate_until_reboot(self):
        self.platform.delays[self.platform.running[0]["unit"]] = 3
        self.shutdown.freeze()
        self.shutdown.stop()
        self.shutdown.assert_empty()
        self.assertEqual(self.platform.now, 3)
        self.assertTrue(self.platform.inhibited)
        self.shutdown.mark_reboot()
        next_boot = Shutdown(
            self.directory.name, self.platform, "boot2", graceful_seconds=5, restore_seconds=5
        )
        self.assertEqual(next_boot.recover()["action"], "external-startup-policy")
        self.assertEqual(self.platform.started, [])
        self.assertFalse(self.platform.inhibited)

    def test_refusal_restores_only_stopped_vms_and_reports_unsettled_late_exit(self):
        first = self.platform.running[0]["unit"]
        second = self.platform.running[1]["unit"]
        self.platform.delays[first] = None
        self.shutdown.freeze()
        with self.assertRaises(Deferred):
            self.shutdown.stop()
        result = self.shutdown.recover()
        self.assertEqual(result["action"], "restoration-failed")
        self.assertEqual(self.platform.started, [second])
        self.assertIn(first, result["failures"][0])
        self.assertFalse(self.platform.inhibited)

    def test_late_guest_exit_during_abort_is_restored(self):
        self.platform.delays[self.platform.running[0]["unit"]] = 7
        self.shutdown.freeze()
        with self.assertRaises(Deferred):
            self.shutdown.stop()
        result = self.shutdown.recover()
        self.assertEqual(result["action"], "restored")
        self.assertEqual(set(self.platform.started), {e["unit"] for e in self.platform.running})

    def test_ambiguous_inventory_aborts_without_touching_any_vm(self):
        self.platform.fail_inventory = True
        with self.assertRaises(Error):
            self.shutdown.freeze()
        self.shutdown.recover()
        self.assertEqual(self.platform.poweroffs, [])
        self.assertEqual(self.platform.started, [])
        self.assertFalse(self.platform.inhibited)

    def test_unexpected_restart_aborts_without_duplicate_start(self):
        self.shutdown.freeze()
        unit = self.platform.running[0]["unit"]
        self.platform.replacement.add(unit)
        with self.assertRaises(Error):
            self.shutdown.stop()
        self.shutdown.recover()
        self.assertNotIn(unit, self.platform.started)

    def test_interrupted_attempt_is_recovered_idempotently(self):
        self.shutdown.freeze()
        self.shutdown.stop()
        restored = Shutdown(
            self.directory.name, self.platform, "boot1", graceful_seconds=5, restore_seconds=5
        )
        self.assertEqual(restored.recover()["action"], "restored")
        self.assertEqual(restored.recover()["action"], "restored")
        self.assertEqual(len(self.platform.started), 2)

    def test_failed_restoration_is_durable_and_blocks_new_attempt(self):
        self.shutdown.freeze()
        self.shutdown.stop()
        self.platform.fail_start.add(self.platform.running[0]["unit"])
        self.assertEqual(self.shutdown.recover()["action"], "restoration-failed")
        self.assertTrue(read_json(self.shutdown.path)["failures"])
        with self.assertRaises(Error):
            self.shutdown.freeze()

    def test_unknown_or_shutting_down_host_does_not_start_vms(self):
        self.shutdown.freeze()
        self.shutdown.stop()
        self.platform.normal = False
        self.assertEqual(self.shutdown.recover()["action"], "restoration-deferred")
        self.assertFalse(self.platform.started)


if __name__ == "__main__":
    unittest.main()
