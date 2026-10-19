"""Project files and filesystem boundaries shared by the CLI and installer."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat

from PIL import Image


def is_redirect(path: Path) -> bool:
    """Includes Windows junction/reparse points on Python versions before 3.12."""
    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def child(root: Path, relative: str | Path) -> Path:
    root = root.resolve()
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Expected a project-relative path without '..'")
    path = root / relative
    cursor = root
    for part in relative.parts:
        cursor /= part
        if is_redirect(cursor):
            raise ValueError(f"Symlink/junction output or input rejected: {relative}")
    if not path.resolve().is_relative_to(root):
        raise ValueError("Path leaves the selected project")
    return path


def read_json(path: Path) -> dict:
    if path.stat().st_size > 5_000_000:
        raise ValueError("JSON file exceeds 5 MB")
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path.name}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def config(root: Path) -> dict:
    value = read_json(child(root, "pet-project.json"))
    if value.get("schema_version") != 1:
        raise ValueError("Unsupported project schema_version")
    name = value.get("display_name")
    if not isinstance(name, str) or not name.strip() or len(name) > 100:
        raise ValueError("display_name must contain 1–100 characters")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_digest(root: Path) -> str:
    """Bind reviews to actual source files and settings, not just an old atlas."""
    root = root.resolve()
    paths = [child(root, "pet-project.json")]
    source = child(root, "source")
    if not source.is_dir():
        raise ValueError("Project source/ directory is missing")
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(root)
        checked = child(root, relative)
        if checked.is_file():
            if checked.stat().st_size > 30_000_000:
                raise ValueError(f"Source file exceeds 30 MB: {relative}")
            paths.append(checked)
    fingerprint = hashlib.sha256()
    for path in paths:
        fingerprint.update(path.relative_to(root).as_posix().encode("utf-8"))
        fingerprint.update(b"\0")
        fingerprint.update(bytes.fromhex(digest(path)))
    return fingerprint.hexdigest()


def validate_atlas(path: Path) -> None:
    from .engine import STATES

    with Image.open(path) as image:
        if image.format != "PNG" or image.mode != "RGBA" or image.size != (1536, 1872):
            raise ValueError("Expected a 1536 × 1872 RGBA PNG v1 atlas")
        image.load()
        for row, (name, count) in enumerate(STATES):
            for column in range(8):
                alpha = image.crop((column * 192, row * 208, (column + 1) * 192, (row + 1) * 208)).getchannel("A")
                box = alpha.getbbox()
                if column >= count:
                    if box is not None:
                        raise ValueError(f"Unused atlas cell is not transparent: {name}/{column}")
                elif box is None:
                    raise ValueError(f"Required atlas cell is blank: {name}/{column}")
                elif min(box[0], box[1], 192 - box[2], 208 - box[3]) < 4:
                    raise ValueError(f"Atlas cell touches its safe border: {name}/{column}")


def current_build(root: Path) -> tuple[Path, dict]:
    config(root)
    quality = read_json(child(root, "final/quality.json"))
    atlas = child(root, "final/spritesheet-v1.png")
    if not quality.get("assembly_ready") or not quality.get("geometric_checks_ok"):
        raise ValueError("Build quality checks have not passed")
    if quality.get("input_sha256") != input_digest(root):
        raise ValueError("Sources changed since the last build; run build, preview and approve again")
    if quality.get("output_sha256") != digest(atlas):
        raise ValueError("Atlas hash differs from the quality report; rebuild it")
    validate_atlas(atlas)
    return atlas, quality
