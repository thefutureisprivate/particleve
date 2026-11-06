import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from particleve.common import Error
from particleve.confinement import CONTROLLER, context, private_directory, start_guard, verify_processes


class ConfinementTests(unittest.TestCase):
    def test_private_directory_rejects_a_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "link").symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(Error, "nonsymlink"):
                private_directory(root / "link")

    def test_collision_rejects_start_before_any_relabel_and_success_only_labels_runtime(self):
        for collision in (False, True):
            with tempfile.TemporaryDirectory() as directory, self.subTest(collision=collision):
                machines = Path(directory) / "machines"
                machines.mkdir()
                (machines / "test").mkdir()
                (machines / "peer").mkdir()
                runtime = Path(directory) / "runtime"
                values = {
                    "/sys/fs/selinux/enforce": "1",
                    "/proc/self/cgroup": "0::/machine.slice/systemd-vmspawn@test.service\n",
                    "/proc/self/attr/current": f"system_u:system_r:{CONTROLLER}:s0:c10,c20",
                }

                def read(path, values=values):
                    return values[str(path)]

                def labels(path, runtime=runtime, collision=collision):
                    if path == runtime / "test":
                        return "system_u:object_r:qemu_var_run_t:s0"
                    pair = "c30,c40" if path.name == "peer" and not collision else "c10,c20"
                    return f"system_u:object_r:virt_var_lib_t:s0:{pair}"

                with (
                    patch("particleve.confinement.os.geteuid", return_value=0),
                    patch("particleve.confinement.os.access", return_value=True),
                    patch("particleve.confinement.GATE") as gate,
                    patch("particleve.confinement.MACHINES", machines),
                    patch("particleve.confinement.RUNTIME", runtime),
                    patch(
                        "particleve.confinement.private_directory", return_value=SimpleNamespace(st_ino=256)
                    ),
                    patch("particleve.confinement.label", side_effect=labels),
                    patch.object(Path, "read_text", read),
                    patch("particleve.confinement.os.setxattr") as relabel,
                ):
                    gate.exists.return_value = False
                    if collision:
                        with self.assertRaisesRegex(Error, "already assigned"):
                            start_guard("test")
                        relabel.assert_not_called()
                    else:
                        start_guard("test")
                        self.assertEqual(relabel.call_args.args[0], runtime / "test")
                        self.assertEqual(relabel.call_count, 1)

    def test_mcs_pair_accepts_kernel_canonical_adjacent_range(self):
        for value in ("c10,c20", "c20,c10", "c10.c11"):
            self.assertEqual(
                context(f"system_u:system_r:{CONTROLLER}:s0:{value}\n", CONTROLLER),
                (10, 11) if value == "c10.c11" else (10, 20),
            )

    def test_unconfined_or_shared_category_ranges_are_rejected(self):
        for value in (
            "system_u:system_r:unconfined_service_t:s0:c10,c20",
            f"system_u:system_r:{CONTROLLER}:s0",
            f"system_u:system_r:{CONTROLLER}:s0:c10",
            f"system_u:system_r:{CONTROLLER}:s0:c10,c10",
            f"system_u:system_r:{CONTROLLER}:s0:c0.c1023",
            f"system_u:system_r:{CONTROLLER}:s0:c0,c1024",
        ):
            with self.subTest(value=value), self.assertRaises(Error):
                context(value, CONTROLLER)

    def test_inhibition_precedes_all_launch_inspection_and_relabeling(self):
        with (
            patch("particleve.confinement.os.geteuid", return_value=0),
            patch("particleve.confinement.GATE") as gate,
            patch("particleve.confinement.os.setxattr") as relabel,
            patch.object(Path, "read_text") as read,
            self.assertRaisesRegex(Error, "temporarily inhibited"),
        ):
            gate.exists.return_value = True
            start_guard("test")
        read.assert_not_called()
        relabel.assert_not_called()

    def test_inventory_rejects_mixed_categories_and_unconfined_children(self):
        for last in (
            "system_u:system_r:swtpm_t:s0:c10,c20",
            "system_u:system_r:swtpm_t:s0:c30,c40",
            "system_u:system_r:unconfined_service_t:s0:c10,c20",
        ):
            with (
                self.subTest(last=last),
                patch.object(
                    Path,
                    "read_text",
                    side_effect=[
                        f"system_u:system_r:{CONTROLLER}:s0:c10,c20",
                        "system_u:system_r:svirt_t:s0:c10,c20",
                        last,
                    ],
                ),
            ):
                processes = [{"pid": n} for n in (1, 2, 3)]
                if ":swtpm_t:s0:c10,c20" in last:
                    verify_processes(processes)
                else:
                    with self.assertRaises(Error):
                        verify_processes(processes)
