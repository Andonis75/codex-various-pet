"""Engine tests use geometric fixtures, never private/generated character art."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from codex_various_pet.engine import ATLAS, CELL, DURATIONS_MS, STATES, process_project


def strip(root: Path, state: str, count: int | None = None, *, mode="RGBA", jump=True):
    count = count if count is not None else dict(STATES)[state]
    image = Image.new(mode, (count * 110 + 20, 210), (0, 0, 0, 0) if mode == "RGBA" else "white")
    draw = ImageDraw.Draw(image)
    for index in range(count):
        x = 28 + index * 110
        lift = [0, 0, 30, 15, 0][index] if state == "jumping" and jump else 0
        draw.rectangle((x, 40 - lift, x + 63, 167 - lift), fill=(220, 160, 80, 255))
        draw.rectangle((x + 8, 54 - lift, x + 26, 74 - lift), fill="white")
        draw.rectangle((x + 36, 54 - lift, x + 50, 74 - lift), fill=(30 + index * 10, 40, 50, 255))
    path = root / "source" / f"{state}-strip.png"
    path.parent.mkdir(exist_ok=True)
    image.save(path)
    return path


def config(root: Path, states):
    (root / "source").mkdir(exist_ok=True)
    (root / "source" / "assembly.json").write_text(json.dumps({"states": states}), encoding="utf-8")


def directory_link(link: Path, destination: Path):
    try:
        link.symlink_to(destination, target_is_directory=True)
        return "symlink"
    except OSError:
        if os.name != "nt":
            raise
        # Junction creation needs no symlink privilege on Windows. All paths
        # here belong to this test's TemporaryDirectory, never a user's files.
        result = subprocess.run(["cmd.exe", "/c", "mklink", "/J", str(link), str(destination)],
                                capture_output=True, check=False)
        if result.returncode:
            raise OSError("No directory-link creation mechanism is available")
        return "junction"


def remove_directory_link(link: Path, kind: str):
    if kind == "junction":
        os.rmdir(link)  # Removes the link itself, never its destination.
    else:
        link.unlink()


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "source").mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def test_full_build_keeps_transparent_padding_and_source(self):
        paths = [strip(self.root, state) for state, _ in STATES]
        before = {p: p.read_bytes() for p in paths}
        report = process_project(self.root, assemble=True)
        self.assertTrue(report["assembled"], report["errors"])
        self.assertTrue(report["assembly_ready"])
        self.assertTrue(report["unused_cells_transparent"])
        self.assertGreaterEqual(report["transforms"]["jumping"]["jump_lift_px"], 8)
        with Image.open(self.root / report["output"]) as atlas:
            self.assertEqual(atlas.size, ATLAS)
            self.assertEqual(atlas.mode, "RGBA")
            self.assertIsNone(atlas.crop((CELL[0] * 6, 0, CELL[0] * 8, CELL[1])).getchannel("A").getbbox())
            self.assertTrue(np.any(np.all(np.array(atlas)[:, :, :3] == 255, axis=2)))
        for state, _ in STATES:
            self.assertTrue((self.root / "preview" / f"{state}.gif").is_file())
        with Image.open(self.root / "preview" / "idle.gif") as gif:
            durations = []
            for index in range(gif.n_frames):
                gif.seek(index)
                durations.append(gif.info["duration"])
            self.assertEqual(durations, DURATIONS_MS["idle"])
        self.assertEqual(before, {p: p.read_bytes() for p in paths})
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_missing_idle_still_previews_other_state(self):
        strip(self.root, "waving")
        report = process_project(self.root)
        self.assertIn("idle", report["missing_states"])
        self.assertTrue(report["rows"]["waving"]["geometry_ok"])
        self.assertTrue((self.root / "preview" / "waving.gif").exists())
        self.assertFalse(report["assembled"])

    def test_holds_are_real_repeated_frames_with_provenance(self):
        strip(self.root, "running-right")
        config(self.root, {"running-right": {"indices": [0, 1, 2, 3, 4, 5, 6, 3]}})
        report = process_project(self.root)
        row = report["rows"]["running-right"]
        self.assertEqual(row["unique_source_frame_count"], 7)
        self.assertEqual(row["hold_frame_count"], 1)
        self.assertEqual(row["output_frames"][-1]["source_index"], 3)
        self.assertTrue(row["output_frames"][-1]["non_adjacent_revisit"])

    def test_invalid_selections_return_reports_and_block(self):
        strip(self.root, "idle")
        for selection in ([-1, 1, 2, 3, 4, 5], [0, 2, 1, 3, 4, 5], [True, 1, 2, 3, 4, 5], "012345"):
            with self.subTest(selection=selection):
                config(self.root, {"idle": {"indices": selection}})
                report = process_project(self.root, assemble=True, previews=False)
                self.assertFalse(report["assembled"])
                self.assertTrue(report["errors"])

    def test_invalid_numbers_and_config_shapes_return_errors(self):
        strip(self.root, "idle")
        for value in (-1, 0, float("nan"), float("inf"), True, "0.5"):
            with self.subTest(value=value):
                config(self.root, {"idle": {"scale": value}})
                report = process_project(self.root, assemble=True, previews=False)
                self.assertTrue(report["errors"])
                self.assertFalse(report["assembled"])
        (self.root / "source" / "assembly.json").write_text("[]")
        self.assertTrue(process_project(self.root, previews=False)["errors"])

    def test_mirror_requires_explicit_boolean_approval(self):
        strip(self.root, "running-right")
        config(self.root, {"running-left": {"mirror": "running-right"}})
        report = process_project(self.root, previews=False)
        self.assertNotIn("running-left", report["available_states"])
        config(self.root, {"running-right": {"approved": True}, "running-left": {"mirror": "running-right"}})
        report = process_project(self.root, previews=False)
        self.assertIn("running-left", report["available_states"])
        self.assertFalse(report["rows"]["running-left"]["temporal_order_reversed"])
        config(self.root, {"running-right": [], "running-left": {"mirror": "running-right"}})
        self.assertTrue(process_project(self.root, previews=False)["errors"])

    def test_mirror_preserves_temporal_order_and_exact_pixels(self):
        for state, _ in STATES:
            if state != "running-left":
                strip(self.root, state)
        config(self.root, {"running-right": {"approved": True}, "running-left": {"mirror": "running-right"}})
        report = process_project(self.root, assemble=True, previews=False)
        self.assertTrue(report["assembled"], report["errors"])
        for index in range(8):
            with Image.open(self.root / "frames" / "running-right" / f"{index:02}.png") as right:
                with Image.open(self.root / "frames" / "running-left" / f"{index:02}.png") as left:
                    np.testing.assert_array_equal(np.array(ImageOps.mirror(right)), np.array(left))

    def test_measured_head_width_overrides_height_fallback(self):
        strip(self.root, "idle")
        config(self.root, {"idle": {"head_width": 80, "target_head_width": 92}})
        report = process_project(self.root, previews=False)
        transform = report["transforms"]["idle"]
        self.assertAlmostEqual(transform["scale"], 92 / 80)
        self.assertAlmostEqual(transform["estimated_output_head_width"], 92)

    def test_soft_edge_cleanup_is_local_and_preserves_opaque(self):
        path = strip(self.root, "idle")
        with Image.open(path) as opened:
            image = opened.copy()
        ImageDraw.Draw(image).line((92, 100, 138, 100), fill=(255, 255, 255, 100), width=1)
        image.save(path)
        config(self.root, {"idle": {"edge_cleanup_alpha_max": 128}})
        report = process_project(self.root, previews=False)
        row = report["rows"]["idle"]
        self.assertTrue(row["original_contact_risks"])
        self.assertTrue(all(c["resolved_by_output_edge_cleanup"] for c in row["original_contact_risks"]))
        for cleanup in row["edge_cleanup"]:
            self.assertEqual(cleanup["opaque_pixels_removed"], 0)
            for x, _, alpha in cleanup["removed_pixels_x_y_alpha"]:
                self.assertIn(x, cleanup["source_x_columns"])
                self.assertLessEqual(alpha, 128)
        ImageDraw.Draw(image).line((92, 100, 138, 100), fill=(255, 255, 255, 255), width=1)
        image.save(path)
        report = process_project(self.root, assemble=True, previews=False)
        self.assertFalse(report["assembled"])
        self.assertFalse(report["rows"]["idle"]["geometry_ok"])

    def test_rgb_and_fake_transparency_rejected(self):
        path = strip(self.root, "idle", mode="RGB")
        self.assertTrue(process_project(self.root, previews=False)["errors"])
        image = Image.new("RGBA", (680, 210), "white")
        image.putpixel((0, 0), (0, 0, 0, 0))
        image.save(path)
        self.assertTrue(process_project(self.root, previews=False)["errors"])

    def test_renamed_non_png_content_is_rejected(self):
        path = strip(self.root, "idle")
        with Image.open(path) as opened:
            image = opened.copy()
        image.save(path, format="TIFF")
        report = process_project(self.root, previews=False)
        self.assertTrue(report["errors"])
        self.assertIn("original PNG", report["rows"]["idle"]["error"])

    def test_source_escape_rejected(self):
        for value in ("../outside.png", "/outside.png", "C:\\outside.png", "..\\outside.png"):
            config(self.root, {"idle": {"source": value}})
            report = process_project(self.root, previews=False)
            self.assertTrue(report["errors"], value)
            self.assertFalse(report["assembly_ready"])

    def test_output_symlink_escape_is_not_written(self):
        strip(self.root, "idle")
        with tempfile.TemporaryDirectory() as destination:
            try:
                kind = directory_link(self.root / "preview", Path(destination))
            except OSError as error:
                self.skipTest(f"Symlinks are not available: {error}")
            try:
                report = process_project(self.root)
                self.assertTrue(report["errors"])
                self.assertEqual(list(Path(destination).iterdir()), [])
            finally:
                remove_directory_link(self.root / "preview", kind)

    def test_source_link_escape_is_not_read(self):
        with tempfile.TemporaryDirectory() as destination:
            destination = Path(destination)
            (destination / "assembly.json").write_text("{}")
            (self.root / "source").rmdir()
            try:
                kind = directory_link(self.root / "source", destination)
            except OSError as error:
                self.skipTest(str(error))
            try:
                report = process_project(self.root, previews=False)
                self.assertTrue(report["errors"])
                self.assertFalse(report["assembly_ready"])
            finally:
                remove_directory_link(self.root / "source", kind)

    def test_source_link_within_project_is_also_rejected(self):
        real_source = self.root / "real-source"
        real_source.mkdir()
        (real_source / "assembly.json").write_text("{}")
        (self.root / "source").rmdir()
        try:
            kind = directory_link(self.root / "source", real_source)
        except OSError as error:
            self.skipTest(str(error))
        try:
            report = process_project(self.root, previews=False)
            self.assertTrue(report["errors"])
            self.assertFalse(report["assembly_ready"])
        finally:
            remove_directory_link(self.root / "source", kind)

    def test_preview_link_to_source_cannot_overwrite_sources(self):
        strip(self.root, "idle")
        sentinel = self.root / "source" / "quality.json"
        sentinel.write_bytes(b"source-must-stay-unchanged")
        try:
            kind = directory_link(self.root / "preview", self.root / "source")
        except OSError as error:
            self.skipTest(str(error))
        try:
            report = process_project(self.root)
            self.assertTrue(report["errors"])
            self.assertFalse(report["assembly_ready"])
            self.assertEqual(sentinel.read_bytes(), b"source-must-stay-unchanged")
            self.assertFalse((self.root / "source" / "inspection.json").exists())
        finally:
            remove_directory_link(self.root / "preview", kind)

    def test_dimensions_are_bounded_before_decoding(self):
        Image.new("RGBA", (32, 4097)).save(self.root / "source" / "idle-strip.png")
        report = process_project(self.root, previews=False)
        self.assertTrue(report["errors"])
        self.assertIn("dimensions", report["rows"]["idle"]["error"])

    def test_preview_parent_file_returns_report(self):
        strip(self.root, "idle")
        (self.root / "preview").write_text("ordinary file")
        report = process_project(self.root)
        self.assertTrue(report["errors"])
        self.assertFalse(report["assembled"])
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_frame_parent_file_blocks_build_without_crashing(self):
        for state, _ in STATES:
            strip(self.root, state)
        (self.root / "frames").mkdir()
        sentinel = self.root / "frames" / "idle"
        sentinel.write_text("ordinary file")
        report = process_project(self.root, assemble=True)
        self.assertFalse(report["assembled"])
        self.assertTrue(report["errors"])
        self.assertEqual(sentinel.read_text(), "ordinary file")

    def test_failed_build_preserves_existing_artwork_and_final_report(self):
        strip(self.root, "idle")
        (self.root / "final").mkdir()
        artwork = self.root / "final" / "spritesheet-v1.png"
        prior = self.root / "final" / "quality.json"
        artwork.write_bytes(b"previous artwork")
        prior.write_text('{"previous":true}')
        report = process_project(self.root, assemble=True, previews=False)
        self.assertFalse(report["assembled"])
        self.assertEqual(artwork.read_bytes(), b"previous artwork")
        self.assertEqual(prior.read_text(), '{"previous":true}')

    def test_stationary_jump_does_not_pass(self):
        for state, _ in STATES:
            strip(self.root, state, jump=False)
        report = process_project(self.root, assemble=True, previews=False)
        self.assertFalse(report["assembled"])
        self.assertFalse(report["jumping_motion_detected"])


if __name__ == "__main__":
    unittest.main()
