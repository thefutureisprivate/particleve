import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from particleve.buildartifacts import carry_signing_hook, postoutput
from particleve.common import Error


class BuildSigningTests(unittest.TestCase):
    def test_none_format_continuation_carries_build_hook_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            recipe = directory / "mkosi.conf"
            recipe.write_text(
                "[Distribution]\nDistribution=custom\n[Output]\nFormat=none\n[Include]\nInclude=mkosi-obs\n"
            )
            carry_signing_hook(directory)
            carry_signing_hook(directory)
            text = recipe.read_text()
            self.assertEqual(text.count("BuildScripts=/usr/libexec/particleve-obs-postoutput"), 1)
            self.assertNotIn("PostOutputScripts=", text)
            self.assertNotIn("BuildPackages=", text)

    def test_incomplete_native_signing_stage_cannot_publish_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "hashes.cpio.rsasign").write_bytes(b"pending native signatures")
            (directory / "mkosi.conf").write_text("[Output]\nFormat=none\n")
            with patch.dict(os.environ, {"OUTPUTDIR": temporary}):
                postoutput()
            self.assertEqual(list(directory.glob("*.release.json")), [])
            (directory / "hashes.cpio.rsasign").unlink()
            with patch.dict(os.environ, {"OUTPUTDIR": temporary}), self.assertRaises(Error):
                postoutput()
            self.assertEqual(list(directory.glob("*.release.json")), [])


if __name__ == "__main__":
    unittest.main()
