import copy
import tempfile
import unittest
from pathlib import Path

from particleve.common import Deferred
from particleve.contracts import PERSISTENT_STATE
from particleve.linux import Linux


class CompatibilityContractTests(unittest.TestCase):
    def test_routine_package_updates_do_not_change_the_retained_state_interface(self):
        old = {
            "persistent_state": copy.deepcopy(PERSISTENT_STATE),
            "packages": [{"name": "kernel-core", "evr": "old"}],
        }
        new = copy.deepcopy(old)
        new["packages"][0]["evr"] = "new"
        backend = Linux.__new__(Linux)
        backend.compatibility_approved(old, new)

    def test_changed_auxiliary_format_or_unit_contract_still_requires_explicit_approval(self):
        for field in ("vm_tpm", "vm_efi", "btrfs", "vm_unit"):
            old = {"persistent_state": copy.deepcopy(PERSISTENT_STATE)}
            new = copy.deepcopy(old)
            new["persistent_state"][field] += "-changed"
            with tempfile.TemporaryDirectory() as directory, self.subTest(field=field):
                backend = Linux.__new__(Linux)
                backend.directory = Path(directory)
                with self.assertRaises(Deferred):
                    backend.compatibility_approved(old, new)
