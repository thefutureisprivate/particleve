"""Use real temporary ESP directories to check boot counters and firmware staging preservation."""

import contextlib
import tempfile
import unittest
from pathlib import Path

from particleve.common import Error, hash_file
from particleve.linux import Linux
from tests.fixtures import release


class ESPTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.backend = Linux.__new__(Linux)
        self.backend.cache = self.root / "cache"
        self.manifest = release("2")
        cache = self.backend.cache / "2"
        cache.mkdir(parents=True)
        for kind, item in self.manifest["artifacts"].items():
            path = cache / item["file"]
            path.write_bytes(kind.encode())
            item["size"] = path.stat().st_size
            item["sha256"] = hash_file(path)
        self.esps = {role: self.root / role for role in ("a", "b")}
        for esp in self.esps.values():
            (esp / "EFI/Linux").mkdir(parents=True)
            (esp / "EFI/UpdateCapsule").mkdir()
            (esp / "EFI/UpdateCapsule/owner.cap").write_bytes(b"firmware")
            (esp / "loader").mkdir()
            (esp / "loader/loader.conf").write_text("timeout 9\neditor no\ndefault old.efi\n")
        self.backend.esp = lambda role: contextlib.nullcontext(self.esps[role])
        self.backend.local_release = lambda version: self.manifest
        self.backend.matching_partition = lambda role, manifest, kind: (
            cache / manifest["artifacts"][kind]["file"]
        )

    def test_existing_boot_counter_and_capsules_survive_preparation(self):
        for role, esp in self.esps.items():
            self.backend.expose_boot(role, self.manifest)
            entry = esp / "EFI/Linux/ParticleVE_2_x86-64+3.efi"
            entry.rename(esp / "EFI/Linux/ParticleVE_2_x86-64+1-2.efi")
            self.backend.expose_boot(role, self.manifest)
            self.assertFalse(entry.exists())
            self.assertTrue((esp / "EFI/Linux/ParticleVE_2_x86-64+1-2.efi").exists())
            self.assertEqual((esp / "EFI/UpdateCapsule/owner.cap").read_bytes(), b"firmware")
        self.backend.prove_fallback("2")
        self.backend.select("2")
        for esp in self.esps.values():
            text = (esp / "loader/loader.conf").read_text()
            self.assertIn("timeout 9", text)
            self.assertIn("default ParticleVE_2_x86-64*.efi", text)

    def test_exhausted_counter_never_becomes_a_fallback_or_gets_reset(self):
        self.backend.expose_boot("a", self.manifest)
        esp = self.esps["a"]
        entry = esp / "EFI/Linux/ParticleVE_2_x86-64+3.efi"
        entry.rename(esp / "EFI/Linux/ParticleVE_2_x86-64+0-3.efi")
        with self.assertRaises(Error):
            self.backend.expose_boot("a", self.manifest)
        with self.assertRaises(Error):
            self.backend.prove_fallback("2")
        self.assertTrue((esp / "EFI/Linux/ParticleVE_2_x86-64+0-3.efi").exists())


if __name__ == "__main__":
    unittest.main()
