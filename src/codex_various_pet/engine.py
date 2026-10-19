"""Deterministic RGBA strip inspection, registration, previews, and v1 assembly.

No artwork is generated here. Geometry reports require a separate visual review
of identity, motion semantics, and loop continuity before any pet installation.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path, PureWindowsPath
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .project import is_redirect

STATES = [("idle", 6), ("running-right", 8), ("running-left", 8),
          ("waving", 4), ("jumping", 5), ("failed", 8),
          ("waiting", 6), ("running", 6), ("review", 6)]
CELL = (192, 208)
ATLAS = (1536, 1872)
ALPHA_THRESHOLD = 7  # Detection retains every pixel with alpha >= 8.
DURATIONS_MS = {
    "idle": [1680, 660, 660, 840, 840, 1920],
    "running-right": [120] * 7 + [220],
    "running-left": [120] * 7 + [220],
    "waving": [140] * 3 + [280],
    "jumping": [140] * 4 + [280],
    "failed": [140] * 7 + [240],
    "waiting": [150] * 5 + [260],
    "running": [120] * 5 + [220],
    "review": [150] * 5 + [280],
}

MAX_CONFIG_BYTES = 262_144
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_SOURCE_PIXELS = 16_000_000
MAX_SOURCE_WIDTH = 16_384
MAX_SOURCE_HEIGHT = 4_096
MAX_COMPONENT_RUNS = 500_000
STATE_OPTIONS = {"source", "indices", "approved", "mirror", "scale", "head_width",
                 "target_head_width", "reference_height", "target_height",
                 "denoise_alpha_below", "edge_cleanup_alpha_max"}


def _source_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\x00" in relative:
        raise ValueError("Source must be a nonempty relative path")
    windows = PureWindowsPath(relative)
    candidate = Path(relative.replace("\\", "/"))
    if candidate.is_absolute() or windows.drive or windows.is_absolute():
        raise ValueError("Absolute source paths are not allowed")
    cursor = root / "source"
    if is_redirect(cursor):
        raise ValueError("Source directory must not be a symlink, junction, or reparse point")
    for part in candidate.parts:
        if part in {".", ".."}:
            raise ValueError("Source paths must not contain traversal components")
        cursor /= part
        if is_redirect(cursor):
            raise ValueError("Source paths must not traverse symlinks, junctions, or reparse points")
    try:
        source = (root / "source").resolve()
    except (OSError, RuntimeError) as error:
        raise ValueError("Source directory cannot be resolved safely") from error
    if not source.is_relative_to(root):
        raise ValueError("Source directory escapes the project")
    try:
        path = (source / candidate).resolve()
    except (OSError, RuntimeError) as error:
        raise ValueError("Source path cannot be resolved safely") from error
    if not path.is_relative_to(source):
        raise ValueError("Source path escapes source directory")
    return path


def _output_path(root: Path, relative: str) -> Path:
    part = Path(relative)
    if part.is_absolute() or not part.parts or part.parts[0] not in {"preview", "final", "frames"}:
        raise ValueError("Invalid output location")
    path = root
    for component in part.parts:
        if component in {".", ".."}:
            raise ValueError("Invalid output path component")
        path = path / component
        if is_redirect(path):
            raise ValueError("Output paths must not traverse symbolic links or junctions")
    try:
        contained = path.resolve().is_relative_to(root)
    except (OSError, RuntimeError) as error:
        raise ValueError("Output path cannot be resolved safely") from error
    if not contained:
        raise ValueError("Output path escapes project directory")
    return path


def _write_bytes(root: Path, relative: str, content: bytes) -> None:
    target = _output_path(root, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    _output_path(root, relative)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".pet-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        _output_path(root, relative)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _write_json(root: Path, relative: str, value: dict) -> None:
    _write_bytes(root, relative, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8"))


def _write_image(root: Path, relative: str, image: Image.Image, **options) -> None:
    encoded = io.BytesIO()
    image.save(encoded, format="GIF" if relative.endswith(".gif") else "PNG", **options)
    _write_bytes(root, relative, encoded.getvalue())


def _number(options: dict, key: str, low: float, high: float, default=None):
    value = options.get(key, default)
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{key} must be a finite number between {low} and {high}")
    return float(value)


def _validate_options(options: dict) -> dict:
    if not isinstance(options, dict):
        raise ValueError("State configuration must be an object")
    unknown = set(options) - STATE_OPTIONS
    if unknown:
        raise ValueError("Unknown state option(s): " + ", ".join(sorted(unknown)))
    for key in ("approved",):
        if key in options and type(options[key]) is not bool:
            raise ValueError(f"{key} must be a boolean")
    if "mirror" in options and options["mirror"] != "running-right":
        raise ValueError("Only mirroring running-right is supported")
    for key, allowed in (("edge_cleanup_alpha_max", (0, 128)), ("denoise_alpha_below", (0, 8))):
        if key in options and (type(options[key]) is not int or options[key] not in allowed):
            raise ValueError(f"{key} must be one of {allowed}")
    for key in ("head_width", "reference_height"):
        _number(options, key, .001, MAX_SOURCE_WIDTH)
    _number(options, "scale", .0001, 100)
    _number(options, "target_head_width", 4, 176)
    _number(options, "target_height", 40, 184)
    return options


def _read_config(root: Path) -> dict:
    path = _source_path(root, "assembly.json")
    if not path.exists():
        return {}
    if path.stat().st_size > MAX_CONFIG_BYTES:
        raise ValueError("assembly.json exceeds the 256 KiB limit")
    def bad_constant(value):
        raise ValueError(f"Non-finite JSON number is not allowed: {value}")
    config = json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=bad_constant)
    if not isinstance(config, dict) or not isinstance(config.get("states", {}), dict):
        raise ValueError("assembly.json and states must be objects")
    settings = config.get("states", {})
    if set(settings) - dict(STATES).keys():
        raise ValueError("assembly.json contains unknown states")
    return settings


def components(mask):
    """8-connected run-length labeling; returns pixel count, bbox and row runs."""
    parent, segments = [], []

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    previous = []
    for y, row in enumerate(mask):
        edges = np.flatnonzero(np.diff(np.pad(row.astype(np.int8), (1, 1))))
        current = []
        previous_start = 0
        for x0, x1 in zip(edges[::2], edges[1::2]):
            ident = len(parent)
            if ident >= MAX_COMPONENT_RUNS:
                raise ValueError("Image is too fragmented to inspect within resource limits")
            parent.append(ident)
            current.append((int(x0), int(x1), ident))
            segments.append((ident, y, int(x0), int(x1)))
            while previous_start < len(previous) and previous[previous_start][1] < x0:
                previous_start += 1
            j = previous_start
            while j < len(previous) and previous[j][0] <= x1:
                parent[find(previous[j][2])] = find(ident)
                j += 1
        previous = current
    groups = {}
    for ident, y, x0, x1 in segments:
        component = groups.setdefault(find(ident), {"pixels": 0, "bbox": [x0, y, x1, y + 1], "runs": []})
        component["pixels"] += x1 - x0
        b = component["bbox"]
        b[:] = [min(b[0], x0), min(b[1], y), max(b[2], x1), max(b[3], y + 1)]
        component["runs"].append((y, x0, x1))
    return sorted(groups.values(), key=lambda c: c["pixels"], reverse=True)


def box_distance(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return math.hypot(dx, dy)


def union_box(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def detect_strip(path, edge_cleanup_alpha_max=0):
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("Source image exceeds the 64 MiB file limit")
    with Image.open(path) as opened:
        if opened.format != "PNG":
            raise ValueError("Source strip must be an original PNG image; renamed formats are not accepted")
        if (not 32 <= opened.width <= MAX_SOURCE_WIDTH or not 32 <= opened.height <= MAX_SOURCE_HEIGHT
                or opened.width * opened.height > MAX_SOURCE_PIXELS):
            raise ValueError("Source image dimensions exceed supported limits (32px minimum, 16 MP maximum)")
        if opened.mode != "RGBA":
            raise ValueError(f"{path.name}: expected genuine RGBA; got {opened.mode}")
        if getattr(opened, "n_frames", 1) != 1:
            raise ValueError("Source strip must be a single image, not an animation")
        image = opened.copy()
    pixels = np.array(image)
    alpha = pixels[:, :, 3]
    transparent_fraction = float(np.mean(alpha == 0))
    if transparent_fraction < .02 or float(np.mean(alpha > 128)) > .90:
        raise ValueError(f"{path.name}: no usable transparency; an opaque or nearly opaque background is not accepted")
    # Opaque-core seeds separate poses joined only by faint antialiased hair.
    # Boundaries then follow measured projection valleys, never equal slots.
    cc = components(alpha > 128)
    if not cc:
        raise ValueError(f"{path.name}: blank strip")
    largest = cc[0]["pixels"]
    mains = [c for c in cc if c["pixels"] >= max(500, largest * .12)
             and c["bbox"][3] - c["bbox"][1] >= image.height * .18]
    mains.sort(key=lambda c: c["bbox"][0])
    if not mains:
        raise ValueError(f"{path.name}: no complete pose silhouette detected")
    if len(mains) > 64:
        raise ValueError("Too many pose components; inspect the source background or detached effects")
    projection = np.count_nonzero(alpha > ALPHA_THRESHOLD, axis=0)
    boundaries, cuts = [0], []
    for left, right in zip(mains, mains[1:]):
        lb, rb = left["bbox"], right["bbox"]
        midpoint = (lb[2] + rb[0]) // 2
        lo = max(boundaries[-1] + 1, min(lb[2], rb[0]) - 10)
        hi = min(image.width - 1, max(lb[2], rb[0]) + 10)
        candidates = list(range(lo, hi + 1))
        if not candidates:
            raise ValueError("Pose components overlap in an ambiguous order")
        boundary = min(candidates, key=lambda x: (int(projection[x - 1]) + int(projection[x]), abs(x - midpoint)))
        boundaries.append(boundary)
        low = int(np.count_nonzero(alpha[:, boundary - 1:boundary + 1] > ALPHA_THRESHOLD))
        opaque = int(np.count_nonzero(alpha[:, boundary - 1:boundary + 1] > 128))
        cuts.append({"x": boundary, "alpha_pixels_at_boundary": low, "opaque_pixels_at_boundary": opaque})
    boundaries.append(image.width)
    if edge_cleanup_alpha_max not in (0, 128):
        raise ValueError("Only explicit edge_cleanup_alpha_max:128 is supported")
    poses, removed, unassigned, cleanup_reports, boundary_residuals = [], [], [], [], []
    for index, main in enumerate(mains):
        x0, x1 = boundaries[index:index + 2]
        local = pixels[:, x0:x1].copy()
        # Optional output-only cleanup is confined to the two extreme columns
        # at measured INTER-POSE splits. Canvas edges are never repaired here.
        edge_mask = np.zeros(local.shape[:2], dtype=bool)
        cleaned_columns = []
        if edge_cleanup_alpha_max:
            if index > 0:
                edge_mask[:, :2] = True
                cleaned_columns.extend([x0, x0 + 1])
            if index < len(mains) - 1:
                edge_mask[:, -2:] = True
                cleaned_columns.extend([x1 - 2, x1 - 1])
        erase = edge_mask & (local[:, :, 3] > 0) & (local[:, :, 3] <= edge_cleanup_alpha_max)
        ey, ex = np.nonzero(erase)
        erased_pixels = [[int(x + x0), int(y), int(local[y, x, 3])] for y, x in zip(ey, ex)]
        local[erase] = 0
        cleanup_reports.append({"source_index": index, "alpha_max": edge_cleanup_alpha_max,
                                "source_x_columns": sorted(set(cleaned_columns)),
                                "removed_pixel_count": len(erased_pixels),
                                "removed_visible_alpha8_128_count": sum(p[2] >= 8 for p in erased_pixels),
                                "removed_sub8_alpha_count": sum(p[2] < 8 for p in erased_pixels),
                                "removed_pixels_x_y_alpha": erased_pixels,
                                "opaque_pixels_removed": 0})
        boundary_residuals.append({"left_visible": int(np.count_nonzero(local[:, :2, 3])),
                                   "right_visible": int(np.count_nonzero(local[:, -2:, 3]))})
        local_cc = components(local[:, :, 3] > ALPHA_THRESHOLD)
        if not local_cc:
            raise ValueError(f"{path.name}: pose {index} empty after projection registration")
        anchor = local_cc[0]
        tiny_limit = max(8, int(largest * .00005))
        distance_limit = max(4, (main["bbox"][3] - main["bbox"][1]) * .018)
        keep = np.zeros(local.shape[:2], dtype=np.uint8)
        group, detached = [], []
        for c in local_cc:
            if c is not anchor and c["pixels"] < tiny_limit:
                # Never erase a visible white or colored detail just because it
                # is small. Only sub-8-alpha isolated noise may be discarded.
                bx0, by0, bx1, by1 = c["bbox"]
                if int(local[by0:by1, bx0:bx1, 3].max()) < 8:
                    removed.append(c)
                    continue
            if c is not anchor and box_distance(c["bbox"], anchor["bbox"]) > distance_limit:
                unassigned.append({"bbox": [c["bbox"][0] + x0, c["bbox"][1], c["bbox"][2] + x0, c["bbox"][3]], "pixels": c["pixels"]})
                # Preserve visible detached pixels in previews and block
                # assembly via the unassigned-components report.
            if c is not anchor:
                cb = c["bbox"]
                detached.append({"bbox": [cb[0] + x0, cb[1], cb[2] + x0, cb[3]],
                                 "pixels": c["pixels"],
                                 "distance_to_main": box_distance(cb, anchor["bbox"]),
                                 "max_alpha": int(local[cb[1]:cb[3], cb[0]:cb[2], 3].max()),
                                 "preserved": True})
            group.append(c)
            for y, xa, xb in c["runs"]:
                keep[y, xa:xb] = 1
        halo = np.array(Image.fromarray(keep * 255).filter(ImageFilter.MaxFilter(3))) > 0
        retained = (keep > 0) | (halo & (local[:, :, 3] > 0) & (local[:, :, 3] <= ALPHA_THRESHOLD))
        local[~retained] = 0
        ys, xs = np.nonzero(retained)
        b = [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]
        crop = Image.fromarray(local, "RGBA").crop(b)
        b[0] += x0
        b[2] += x0
        poses.append({"bbox": b, "image": crop, "pixels": sum(c["pixels"] for c in group),
                      "component_count": len(group), "opaque_core_bbox": main["bbox"],
                      "retained_detached_components": detached})
    gaps = [poses[i + 1]["bbox"][0] - poses[i]["bbox"][2] for i in range(len(poses) - 1)]
    edges = [{"frame": i, "margins": [b[0], b[1], image.width - b[2], image.height - b[3]]}
             for i, p in enumerate(poses) if min((b := p["bbox"])[0], b[1], image.width - b[2], image.height - b[3]) < 3]
    original_contacts = []
    for i, cut in enumerate(cuts):
        if not cut["alpha_pixels_at_boundary"]:
            continue
        residual = boundary_residuals[i]["right_visible"] + boundary_residuals[i + 1]["left_visible"]
        resolved = bool(edge_cleanup_alpha_max and residual == 0 and cut["opaque_pixels_at_boundary"] == 0)
        original_contacts.append({"between": [i, i + 1], **cut,
                                  "residual_boundary_pixels": residual,
                                  "resolved_by_output_edge_cleanup": resolved})
    report = {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "size": list(image.size), "mode": image.mode, "detected_count": len(poses),
              "fully_transparent_fraction": transparent_fraction,
              "alpha_threshold": ALPHA_THRESHOLD, "seed_alpha_threshold": 128, "components": len(cc),
              "removed_tiny_components": len(removed), "removed_tiny_pixels": sum(c["pixels"] for c in removed),
              "unassigned_components": unassigned,
              "poses": [{k: v for k, v in p.items() if k != "image"} for p in poses],
              "projection_cuts": cuts, "inter_pose_gaps_px": gaps, "source_clipping_risks": edges,
              "edge_cleanup": cleanup_reports, "original_contact_risks": original_contacts,
              "contact_risks": [r for r in original_contacts if not r["resolved_by_output_edge_cleanup"]],
              "white_opaque_pixels": int(np.count_nonzero((alpha > 200) & np.all(pixels[:, :, :3] > 220, axis=2))),
              "semantic_review": "required; geometry cannot establish identity, blink, gait or expression"}
    report["detached_visible_components"] = [{"source_index": i, **c} for i, pose in enumerate(poses)
                                             for c in pose["retained_detached_components"]
                                             if c["pixels"] >= 24 and c["max_alpha"] > 32]
    return image, poses, report


def checker(size):
    board = Image.new("RGB", size, "#d9dde2")
    draw = ImageDraw.Draw(board)
    for y in range(0, size[1], 16):
        for x in range(0, size[0], 16):
            if (x // 16 + y // 16) % 2:
                draw.rectangle((x, y, x + 15, y + 15), fill="#f4f5f6")
    return board


def contact_sheet(rows):
    out = checker((8 * CELL[0], max(1, len(rows)) * (CELL[1] + 26)))
    draw = ImageDraw.Draw(out)
    if not rows:
        draw.text((12, 12), "No valid frames to preview; see quality.json.", fill="#152234")
    for row, (name, frames, indices) in enumerate(rows):
        y = row * (CELL[1] + 26)
        for i, frame in enumerate(frames):
            out.paste(frame, (i * CELL[0], y + 26), frame)
            draw.text((i * CELL[0] + 5, y + 7), f"{name} {i + 1} [source {indices[i]}]", fill="#152234")
    return out


def selection_details(indices, expected_count, source_count):
    if not isinstance(indices, list) or len(indices) != expected_count or any(type(i) is not int or i < 0 or i >= source_count for i in indices):
        raise ValueError(f"Need {expected_count} valid source indices in 0..{source_count - 1}; got {indices}")
    first_occurrences, first_output, frames = [], {}, []
    for output_index, source_index in enumerate(indices):
        repeated = source_index in first_output
        if not repeated:
            if first_occurrences and source_index < first_occurrences[-1]:
                raise ValueError(f"Source pose reordering is not supported: first occurrence {source_index} follows {first_occurrences[-1]}")
            first_occurrences.append(source_index)
            first_output[source_index] = output_index
        frames.append({"output_frame": output_index, "source_index": source_index,
                       "kind": "hold" if repeated else "source",
                       "repeat_of_output_frame": first_output[source_index] if repeated else None,
                       "non_adjacent_revisit": repeated and indices[output_index - 1] != source_index})
    return {"output_frames": frames, "unique_source_frame_count": len(first_occurrences),
            "hold_frame_count": len(indices) - len(first_occurrences),
            "independent_generated_frame_count_claimed": False}


def normalize(data):
    normalized, transforms = {}, {}
    for name, row in data.items():
        poses = [row["poses"][i] for i in row["indices"]]
        max_width = max(p["image"].width for p in poses)
        max_height = max(p["image"].height for p in poses)
        # The source generator can change render scale between strips. Normalize
        # at row level, keeping every pose on that row at the same scale. A truly
        # crouched/reclining row may declare a smaller target_height explicitly.
        target_height = row.get("target_height", 176)
        scale_settings = row.get("scale_settings", {})
        if "scale" in scale_settings:
            requested_scale = scale_settings["scale"]
            scale_basis = "explicit source pixel scale"
        elif "head_width" in scale_settings:
            requested_scale = scale_settings.get("target_head_width", 92) / scale_settings["head_width"]
            scale_basis = "measured source head width"
        elif "reference_height" in scale_settings:
            requested_scale = 176 / scale_settings["reference_height"]
            scale_basis = "standing-equivalent source reference height"
        else:
            requested_scale = target_height / max_height
            scale_basis = "row maximum pose height (configurable fallback)"
        source_baseline = max(p["bbox"][3] for p in poses)
        vertical_span = source_baseline - min(p["bbox"][1] for p in poses) if name == "jumping" else max_height
        scale = min(requested_scale, 176 / max_width, 184 / vertical_span)
        frames, placements = [], []
        for source_index, pose in zip(row["indices"], poses):
            crop = pose["image"].copy()
            denoised_pixels = 0
            if row.get("denoise_alpha_below") == 8:
                crop_array = np.array(crop)
                weak = (crop_array[:, :, 3] > 0) & (crop_array[:, :, 3] < 8)
                denoised_pixels = int(np.count_nonzero(weak))
                crop_array[weak] = 0
                crop = Image.fromarray(crop_array, "RGBA")
            size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
            fitted = crop.resize(size, Image.Resampling.LANCZOS)
            # Foot registration is stable within non-jump rows. Jumping keeps real
            # source vertical displacements instead of grounding every pose.
            lift = round((source_baseline - pose["bbox"][3]) * scale) if name == "jumping" else 0
            x, y = (CELL[0] - size[0]) // 2, 196 - lift - size[1]
            if x < 4 or y < 4 or x + size[0] > 188 or y + size[1] > 204:
                raise ValueError(f"{name}: transformed pose exceeds safe cell bounds")
            frame = Image.new("RGBA", CELL)
            frame.alpha_composite(fitted, (x, y))
            array = np.array(frame)
            array[array[:, :, 3] == 0, :3] = 0
            frames.append(Image.fromarray(array, "RGBA"))
            alpha_box = frames[-1].getchannel("A").getbbox()
            if alpha_box is None:
                raise ValueError(f"{name}: empty exported frame")
            border = min(alpha_box[0], alpha_box[1], CELL[0] - alpha_box[2], CELL[1] - alpha_box[3])
            if border < 4:
                raise ValueError(f"{name}: exported frame lacks four transparent border pixels")
            placements.append({"x": x, "y": y, "size": size, "source_index": source_index,
                               "source_lift": source_baseline - pose["bbox"][3], "output_lift": lift,
                               "removed_sub8_alpha_pixels": denoised_pixels,
                               "exported_alpha_bbox": alpha_box, "transparent_border_min_px": border})
        normalized[name] = frames
        transforms[name] = {"scale": scale, "baseline": 196, "source_baseline": source_baseline,
                            "source_canvas_size": row["size"], "placements": placements,
                            "jump_lift_px": max(p["output_lift"] for p in placements),
                            "target_height": target_height, "output_max_height": max(p["size"][1] for p in placements),
                            "safety_scale_factor": scale / requested_scale,
                            "scale_basis": scale_basis,
                            "estimated_output_head_width": scale * scale_settings["head_width"] if "head_width" in scale_settings else None,
                            "scale_policy": "one transform per row; explicit scale/head/reference overrides configurable height fallback; capped for cell safety"}
    return normalized, transforms


def _error_message(error: Exception, root: Path) -> str:
    return str(error).replace(str(root), "<project>").replace(root.as_posix(), "<project>")


def _load_rows(root: Path, settings: dict, errors: list) -> tuple[dict, dict]:
    data, reports = {}, {}
    for name, count in STATES:
        try:
            options = _validate_options(settings.get(name, {}))
            if "mirror" in options:
                if name != "running-left" or set(options) != {"mirror"}:
                    raise ValueError("A mirrored running-left row only accepts mirror; all settings and temporal order are inherited")
                right_options = settings.get("running-right", {})
                if not isinstance(right_options, dict) or right_options.get("approved") is not True:
                    raise ValueError("Mirroring needs explicit running-right.approved=true")
                if "running-right" not in data:
                    raise ValueError("Mirroring needs a readable running-right source with valid selection")
                right = data["running-right"]
                data[name] = {**right, "poses": [{**pose, "image": ImageOps.mirror(pose["image"])} for pose in right["poses"]]}
                reports[name] = copy.deepcopy(reports["running-right"])
                reports[name].update(derived_from="running-right", mirrored_each_frame=True, temporal_order_reversed=False)
                continue
            filename = options.get("source", f"{name}-strip.png")
            path = _source_path(root, filename)
            if not path.exists():
                continue
            image, poses, row_report = detect_strip(path, options.get("edge_cleanup_alpha_max", 0))
            row_report["file"] = path.relative_to((root / "source").resolve()).as_posix()
            reports[name] = row_report
            indices = options.get("indices", list(range(len(poses))))
            row_report.update(selection_details(indices, count, len(poses)))
            row_report.update(selected_indices=indices, expected_count=count)
            row_report["selected_clipping_risks"] = [r for r in row_report["source_clipping_risks"] if r["frame"] in indices]
            row_report["selected_contact_risks"] = [r for r in row_report["contact_risks"] if any(i in indices for i in r["between"])]
            row_report["selected_detached_visible_components"] = [r for r in row_report["detached_visible_components"] if r["source_index"] in indices]
            row_report["geometry_ok"] = not any(row_report[key] for key in (
                "selected_clipping_risks", "selected_contact_risks", "unassigned_components", "selected_detached_visible_components"))
            scale_settings = {key: float(options[key]) for key in ("scale", "head_width", "target_head_width", "reference_height") if key in options}
            row_report.update(scale_settings=scale_settings, denoise_alpha_below=options.get("denoise_alpha_below", 0))
            data[name] = {"size": image.size, "poses": poses, "indices": indices,
                          "target_height": float(options.get("target_height", 176)),
                          "scale_settings": scale_settings,
                          "denoise_alpha_below": options.get("denoise_alpha_below", 0)}
        except (ValueError, TypeError, OSError, Image.DecompressionBombError) as error:
            message = _error_message(error, root)
            reports.setdefault(name, {"expected_count": count}).update(geometry_ok=False, error=message)
            errors.append({"state": name, "code": "invalid_source_or_config", "message": message})
    return data, reports


def _make_previews(root: Path, data: dict, frames: dict) -> list[str]:
    outputs = []
    for name, _ in STATES:
        if name not in frames:
            continue
        gif_frames = []
        for frame in frames[name]:
            board = checker(CELL)
            board.paste(frame, (0, 0), frame)
            gif_frames.append(board)
        relative = f"preview/{name}.gif"
        _write_image(root, relative, gif_frames[0], save_all=True, append_images=gif_frames[1:],
                     duration=DURATIONS_MS[name], loop=0, disposal=2)
        outputs.append(relative)
        if name == "idle":
            relative = "preview/idle-fast.gif"
            _write_image(root, relative, gif_frames[0], save_all=True, append_images=gif_frames[1:],
                         duration=[120] * len(gif_frames), loop=0, disposal=2)
            outputs.append(relative)
    _write_image(root, "preview/contact-sheet.png", contact_sheet([
        (name, frames[name], data[name]["indices"]) for name, _ in STATES if name in frames]))
    outputs.append("preview/contact-sheet.png")
    return outputs


def process_project(root: Path, assemble: bool = False, previews: bool = True) -> dict:
    """Inspect a project and optionally assemble its deterministic v1 artwork.

    Recoverable source, configuration, geometry and output-path failures are
    returned in ``errors``/``rows`` and make ``assembly_ready`` false. A build
    only succeeds when ``assembled`` is true. Existing final artwork is never
    deleted when current inspection fails. Missing states are always reported,
    and partial previews do not require an idle strip. Reports use project-
    relative output/source paths and never grant visual or semantic approval.
    """
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Project root must be an existing directory")
    if type(assemble) is not bool or type(previews) is not bool:
        raise TypeError("assemble and previews must be booleans")
    errors: list[dict] = []
    try:
        settings = _read_config(root)
    except (ValueError, OSError) as error:
        errors.append({"code": "invalid_configuration", "message": _error_message(error, root)})
        settings = {}
    data, rows = _load_rows(root, settings, errors)
    frames, transforms = {}, {}
    for name, row in data.items():
        try:
            normalized, transform = normalize({name: row})
            frames[name] = normalized[name]
            transforms[name] = transform[name]
        except (ValueError, OSError) as error:
            rows[name].update(geometry_ok=False, normalization_error=_error_message(error, root))
            errors.append({"state": name, "code": "normalization_failed", "message": _error_message(error, root)})
    missing = [name for name, _ in STATES if name not in data]
    geometry_ok = bool(rows) and all(row.get("geometry_ok", False) for row in rows.values())
    jump_lift = transforms.get("jumping", {}).get("jump_lift_px")
    if jump_lift is not None and jump_lift < 8:
        rows["jumping"]["geometry_ok"] = False
        rows["jumping"]["jump_error"] = "Jump must preserve at least 8 output pixels of visible lift"
        geometry_ok = False
    quality = {"schema": "v1", "atlas_size": list(ATLAS), "cell_size": list(CELL),
               "available_states": list(data), "missing_states": missing, "rows": rows,
               "complete": not missing, "geometric_checks_ok": geometry_ok,
               "transforms": transforms, "errors": errors, "outputs": [],
               "jumping_motion_detected": jump_lift is not None and jump_lift >= 8,
               "visual_semantic_approval": "not asserted by this engine",
               "preview_durations_ms": copy.deepcopy(DURATIONS_MS), "idle_fast_preview_duration_ms": 120,
               "assembly_requested": assemble, "assembled": False,
               "assembly_ready": not missing and geometry_ok and not errors and len(frames) == len(STATES)}
    # Preflight exact outputs before writing any frame/artwork, so a linked
    # directory cannot redirect a later stage into source or outside the run.
    outputs_to_check = ["preview/inspection.json", "preview/quality.json"]
    if previews:
        outputs_to_check += ["preview/contact-sheet.png", "preview/idle-fast.gif"]
        outputs_to_check += [f"preview/{name}.gif" for name in frames]
    if assemble and quality["assembly_ready"]:
        outputs_to_check += ["final/spritesheet-v1.png", "final/quality.json"]
        outputs_to_check += [f"frames/{name}/{i:02}.png" for name, count in STATES for i in range(count)]
    for relative in outputs_to_check:
        try:
            _output_path(root, relative)
        except (ValueError, OSError) as error:
            errors.append({"code": "unsafe_output_path", "path": relative, "message": _error_message(error, root)})
            quality["assembly_ready"] = False
    try:
        if previews and not any(e["code"] == "unsafe_output_path" for e in errors):
            quality["outputs"] += _make_previews(root, data, frames)
        if assemble and quality["assembly_ready"]:
            atlas = Image.new("RGBA", ATLAS)
            for row_index, (name, count) in enumerate(STATES):
                for frame_index in range(count):
                    frame = frames[name][frame_index]
                    atlas.alpha_composite(frame, (frame_index * CELL[0], row_index * CELL[1]))
                    relative = f"frames/{name}/{frame_index:02}.png"
                    _write_image(root, relative, frame)
            _write_image(root, "final/spritesheet-v1.png", atlas)
            quality["assembled"] = True
            quality["output"] = "final/spritesheet-v1.png"
            quality["output_sha256"] = hashlib.sha256(_output_path(root, quality["output"]).read_bytes()).hexdigest()
            quality["unused_cells_transparent"] = all(
                atlas.crop((i * CELL[0], r * CELL[1], (i + 1) * CELL[0], (r + 1) * CELL[1])).getchannel("A").getbbox() is None
                for r, (_, count) in enumerate(STATES) for i in range(count, 8))
            quality["outputs"] += ["final/spritesheet-v1.png", "final/quality.json"]
            _write_json(root, "final/quality.json", quality)
    except (ValueError, OSError) as error:
        errors.append({"code": "output_failed", "message": _error_message(error, root)})
        quality.update(assembled=False, assembly_ready=False)
    if assemble and not quality["assembled"]:
        quality["assembly_blocked"] = True
    try:
        _write_json(root, "preview/inspection.json", quality)
        _write_json(root, "preview/quality.json", quality)
    except (ValueError, OSError) as error:
        errors.append({"code": "report_output_failed", "message": _error_message(error, root)})
        quality.update(assembled=False, assembly_ready=False)
    return quality
