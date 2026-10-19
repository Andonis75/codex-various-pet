"""Validated, additive installation into the user's Codex pets directory."""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

from .project import child, config, current_build, is_redirect, read_json, write_json


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()


def valid_slug(slug: str) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", slug):
        raise ValueError("Slug must contain 1–63 lowercase letters, digits or hyphens")
    if slug.split(".", 1)[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}:
        raise ValueError("Slug is a reserved Windows device name")


def manifest(root: Path) -> dict:
    project = config(root)
    return {"displayName": project["display_name"], "description": "Created with codex-various-pet", "spriteVersionNumber": 1, "spritesheetPath": "spritesheet.png"}


def approved_build(root: Path) -> Path:
    atlas, quality = current_build(root)
    approval = read_json(child(root, "final/approval.json"))
    if approval.get("sprite_sha256") != quality["output_sha256"] or approval.get("input_sha256") != quality["input_sha256"] or approval.get("visually_reviewed") is not True:
        raise ValueError("Visual approval is missing or stale; inspect the preview, then run approve")
    return atlas


def install_pet(root: Path, slug: str, pets_dir: Path | None = None) -> Path:
    valid_slug(slug)
    atlas = approved_build(root)
    pets = (pets_dir if pets_dir is not None else codex_home() / "pets").expanduser().absolute()
    # A user may choose an existing absolute base, but not a redirecting pets directory.
    if is_redirect(pets):
        raise ValueError("Pets directory must not be a symlink or junction")
    pets.mkdir(parents=True, exist_ok=True)
    target = pets / slug
    if target.exists() or target.is_symlink():
        raise ValueError(f"Pet already exists: {slug}. Choose another slug; existing pets are preserved")
    stage = Path(tempfile.mkdtemp(prefix=".various-pet-", dir=pets))
    try:
        shutil.copyfile(atlas, stage / "spritesheet.png")
        write_json(stage / "pet.json", manifest(root))
        # rename, never replace: an intervening install must fail instead of overwriting.
        stage.rename(target)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return target


def package_pet(root: Path, slug: str) -> Path:
    valid_slug(slug)
    atlas = approved_build(root)
    destination = child(root, "final/pet-package.zip")
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        import json
        archive.writestr(f"{slug}/pet.json", json.dumps(manifest(root), ensure_ascii=False, indent=2).encode("utf-8"))
        archive.write(atlas, f"{slug}/spritesheet.png")
    return destination
