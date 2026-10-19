"""Behavioral CLI, review-boundary, installation and export regressions.

All writes stay in TemporaryDirectory; no real CODEX_HOME is used.
"""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

from PIL import Image, ImageDraw

from codex_various_pet.cli import create_project, install_skill, main
from codex_various_pet.engine import STATES
from codex_various_pet.install import install_pet, package_pet
from codex_various_pet.preview import render
from codex_various_pet.project import child, current_build, read_json, write_json


def invoke(*arguments):
    output = io.StringIO()
    with redirect_stdout(output), redirect_stderr(output):
        status = main([str(argument) for argument in arguments])
    return status, output.getvalue()


def make_strips(root):
    """Connected opaque silhouettes on genuinely transparent PNG canvases."""
    states = {"running-right": {"approved": True},
              "running-left": {"mirror": "running-right"}}
    for state, count in STATES:
        if state == "running-left":
            continue
        image = Image.new("RGBA", (count * 150 + 40, 240))
        draw = ImageDraw.Draw(image)
        for index in range(count):
            x = 45 + index * 150
            lift = [0, 0, 26, 13, 0][index] if state == "jumping" else 0
            y = 68 - lift
            draw.ellipse((x, y, x + 66, y + 68), fill=(255, 255, 255, 255))
            draw.rectangle((x + 10, y + 49, x + 54, y + 129), fill=(35, 48 + index, 65, 255))
            draw.rectangle((x + 46, y + 88, x + 67, y + 103), fill=(35, 48 + index, 65, 255))
        image.save(root / "source" / f"{state}-strip.png")
    write_json(root / "source/assembly.json", {"states": states})


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_dir = tempfile.TemporaryDirectory(prefix="various-pet-fixture-")
        cls.fixture = Path(cls.fixture_dir.name) / "fixture"
        create_project(cls.fixture, "测试桌宠", None)
        make_strips(cls.fixture)
        status, output = invoke("build", cls.fixture)
        if status:
            raise AssertionError(f"Synthetic transparent source build failed: {output}")
        status, output = invoke("approve", cls.fixture)
        if status:
            raise AssertionError(output)

    @classmethod
    def tearDownClass(cls):
        cls.fixture_dir.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="various-pet-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.root = self.directory / "project"
        shutil.copytree(self.fixture, self.root)
        self.pets = self.directory / "pets"

    def test_valid_reviewed_install_has_exact_utf8_manifest_and_rgba_atlas(self):
        target = install_pet(self.root, "test-pet", self.pets)
        self.assertEqual(target, self.pets / "test-pet")
        raw = (target / "pet.json").read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        manifest = json.loads(raw.decode("utf-8"))
        self.assertEqual(manifest["displayName"], "测试桌宠")
        self.assertEqual(manifest["spriteVersionNumber"], 1)
        with Image.open(target / manifest["spritesheetPath"]) as atlas:
            self.assertEqual(atlas.size, (1536, 1872))
            self.assertEqual(atlas.mode, "RGBA")
            self.assertIsNone(atlas.crop((6 * 192, 0, 1536, 208)).getchannel("A").getbbox())

    def test_invalid_slugs_never_create_destination(self):
        for slug in ("../escape", "..", "/absolute", "a/b", "a\\b", "a:stream", "A", "", "-x", "a" * 64,
                     "con", "prn", "aux", "nul", "com1", "lpt9", "a.", "a\x00b"):
            with self.subTest(slug=slug), self.assertRaises(ValueError):
                install_pet(self.root, slug, self.pets)
        self.assertFalse(self.pets.exists())

    def test_existing_pet_is_preserved(self):
        existing = self.pets / "test-pet"
        existing.mkdir(parents=True)
        marker = existing / "pet.json"
        marker.write_bytes(b"existing user's content")
        with self.assertRaisesRegex(ValueError, "already exists"):
            install_pet(self.root, "test-pet", self.pets)
        self.assertEqual(marker.read_bytes(), b"existing user's content")
        self.assertEqual(sorted(path.name for path in self.pets.iterdir()), ["test-pet"])

    def test_absent_review_refuses_install_and_export(self):
        (self.root / "final/approval.json").unlink()
        for operation in (lambda: install_pet(self.root, "test", self.pets), lambda: package_pet(self.root, "test")):
            with self.assertRaises((ValueError, OSError)):
                operation()
        self.assertFalse(self.pets.exists())

    def test_source_change_invalidates_review(self):
        image_path = self.root / "source/idle-strip.png"
        with Image.open(image_path) as image:
            image.putpixel((50, 100), (240, 0, 0, 255))
            image.save(image_path)
        with self.assertRaisesRegex(ValueError, "Sources changed"):
            install_pet(self.root, "test", self.pets)
        self.assertFalse(self.pets.exists())

    def test_atlas_change_invalidates_review(self):
        atlas = self.root / "final/spritesheet-v1.png"
        with Image.open(atlas) as image:
            image.putpixel((80, 90), (100, 100, 100, 255))
            image.save(atlas)
        with self.assertRaisesRegex(ValueError, "hash differs"):
            install_pet(self.root, "test", self.pets)

    def test_false_or_mismatched_review_is_rejected(self):
        for key, value in (("visually_reviewed", False), ("sprite_sha256", "0" * 64), ("input_sha256", "0" * 64)):
            approval = read_json(self.fixture / "final/approval.json")
            approval[key] = value
            write_json(self.root / "final/approval.json", approval)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "approval"):
                install_pet(self.root, "test", self.pets)

    def test_failed_build_cannot_reuse_previously_approved_atlas(self):
        # Break an output directory without changing the source digest. A prior
        # approved atlas must not be silently installed after this failed build.
        frame_dir = self.root / "frames/idle"
        shutil.rmtree(frame_dir)
        frame_dir.write_text("output blocked", encoding="utf-8")
        status, _ = invoke("build", self.root)
        self.assertEqual(status, 2)
        with self.assertRaises((ValueError, OSError)):
            install_pet(self.root, "test", self.pets)
        self.assertFalse(self.pets.exists())

    def test_explicit_rebuild_requires_new_review_even_when_pixels_are_identical(self):
        status, output = invoke("build", self.root)
        self.assertEqual(status, 0, output)
        with self.assertRaises((ValueError, OSError)):
            install_pet(self.root, "test", self.pets)
        status, output = invoke("approve", self.root)
        self.assertEqual(status, 0, output)
        self.assertTrue(install_pet(self.root, "test", self.pets).is_dir())

    def test_package_contains_only_portable_manifest_and_sprite(self):
        archive_path = package_pet(self.root, "test-pet")
        with zipfile.ZipFile(archive_path) as archive:
            self.assertEqual(sorted(archive.namelist()), ["test-pet/pet.json", "test-pet/spritesheet.png"])
            raw = archive.read("test-pet/pet.json")
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertEqual(json.loads(raw)["spritesheetPath"], "spritesheet.png")
            self.assertNotIn(str(self.directory).encode(), raw)

    def test_preview_escapes_untrusted_json_without_changing_display_name(self):
        evil = '</script><script>alert("PET_XSS")</script><img src=x onerror=alert(1)>&'
        project = read_json(self.root / "pet-project.json")
        project["display_name"] = evil
        write_json(self.root / "pet-project.json", project)
        status, output = invoke("build", self.root)
        self.assertEqual(status, 0, output)
        html = render(self.root).read_text(encoding="utf-8")
        self.assertNotIn('<script>alert("PET_XSS")', html)
        self.assertNotIn('<img src=x onerror', html)
        payload = re.search(r'<script id="preview-data" type="application/json">(.*?)</script>', html, re.S)
        self.assertIsNotNone(payload)
        self.assertEqual(json.loads(payload.group(1))["displayName"], evil)
        self.assertNotIn("<", payload.group(1))
        self.assertNotIn("innerHTML", html)
        self.assertNotIn("fetch(", html)

    def test_project_relative_files_reject_parent_traversal(self):
        for relative in ("../escape", "source/../../escape", str(self.directory / "escape")):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                child(self.root, relative)

    def test_init_reference_validation_precedes_directory_creation(self):
        invalid = self.directory / "not-an-image.png"
        invalid.write_bytes(b"not a PNG")
        destination = self.directory / "invalid-project"
        status, output = invoke("init", destination, "--reference", invalid)
        self.assertEqual(status, 2, output)
        self.assertFalse(destination.exists())

    def test_new_project_accepts_nine_independent_source_strips_without_mirror_approval(self):
        destination = self.directory / "new-project"
        create_project(destination, "Nine independent strips", None)
        initial_config = (destination / "source/assembly.json").read_bytes()
        make_strips(destination)
        shutil.copyfile(destination / "source/running-right-strip.png",
                        destination / "source/running-left-strip.png")
        (destination / "source/assembly.json").write_bytes(initial_config)
        status, output = invoke("build", destination)
        self.assertEqual(status, 0, output)
        _, quality = current_build(destination)
        self.assertFalse(quality["rows"]["running-left"].get("mirrored_each_frame", False))

    def test_standalone_installed_skill_runs_outside_checkout(self):
        destination = install_skill(self.directory / "skill")
        runner = destination / "scripts/run.py"
        self.assertTrue(runner.is_file())
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        result = subprocess.run([sys.executable, str(runner), "--version"], cwd=self.directory,
                                env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run([sys.executable, str(runner), "demo", str(self.directory / "skill-demo")],
                                cwd=self.directory, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.directory / "skill-demo/source/idle-strip.png").is_file())
        self.assertTrue((destination / "scripts/codex_various_pet/data/player.html").is_file())

    def test_existing_skill_is_preserved(self):
        destination = self.directory / "skill"
        destination.mkdir()
        marker = destination / "SKILL.md"
        marker.write_text("existing", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "already exists"):
            install_skill(destination)
        self.assertEqual(marker.read_text(), "existing")


if __name__ == "__main__":
    unittest.main()
