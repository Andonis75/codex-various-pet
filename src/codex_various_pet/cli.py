"""Small, explicit steps from browser artwork to a locally installed pet."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from importlib.resources import files
import json
from pathlib import Path
import shutil
import sys
import tempfile
import webbrowser

from PIL import Image

from . import __version__
from .install import codex_home, install_pet, package_pet
from .project import child, config, current_build, input_digest, write_json


def create_project(root: Path, name: str, reference: Path | None) -> Path:
    if not name.strip() or len(name) > 100:
        raise ValueError("Name must contain 1–100 characters")
    if reference is not None:
        if not reference.is_file() or reference.stat().st_size > 20_000_000:
            raise ValueError("Reference must be a local image no larger than 20 MB")
        with Image.open(reference) as image:
            if image.format not in {"PNG", "JPEG", "WEBP"} or image.width * image.height > 30_000_000:
                raise ValueError("Reference must be PNG, JPEG or WebP, no larger than 30 megapixels")
            image.verify()
    root.mkdir(parents=True, exist_ok=False)
    (root / "source").mkdir()
    settings = {"schema_version": 1, "display_name": name}
    if reference is not None:
        suffix = {".jpeg": ".jpg"}.get(reference.suffix.lower(), reference.suffix.lower())
        # Use a neutral name: source paths, usernames and the chat URL are not stored.
        destination = root / ("reference" + suffix)
        shutil.copyfile(reference, destination)
        settings["reference"] = destination.name
    write_json(root / "pet-project.json", settings)
    write_json(root / "source/assembly.json", {"states": {}})
    (root / "identity.md").write_text("以已上传的参考图为准，保留角色可辨认的外观、身体结构、配饰和画风。\n", encoding="utf-8")
    from .prompts import generate
    generate(root)
    return root


def install_skill(destination: Path) -> Path:
    """Install a runnable skill with its own source; no checkout-relative imports."""
    if destination.exists() or destination.is_symlink():
        raise ValueError("Skill directory already exists; choose --destination with a new directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".various-pet-skill-", dir=destination.parent))
    try:
        payload = Path(str(files("codex_various_pet").joinpath("data/skill")))
        shutil.copytree(payload, stage, dirs_exist_ok=True)
        package_source = Path(__file__).parent
        package_target = stage / "scripts/codex_various_pet"
        package_target.mkdir(parents=True)
        for source in package_source.glob("*.py"):
            shutil.copyfile(source, package_target / source.name)
        # The skill reference directory is not duplicated inside its runner package.
        shutil.copytree(package_source / "data", package_target / "data", ignore=shutil.ignore_patterns("skill"))
        stage.rename(destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return destination


def demo(root: Path) -> Path:
    if root.exists() or root.is_symlink():
        raise ValueError("Demo destination already exists")
    source = Path(str(files("codex_various_pet").joinpath("data/demo")))
    shutil.copytree(source, root)
    return root


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(prog="various-pet", description="Browser artwork → verified Codex desktop pet. No image API or browser credentials required.")
    command.add_argument("--version", action="version", version=__version__)
    sub = command.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create a project and reusable web prompts")
    init.add_argument("project", type=Path)
    init.add_argument("--reference", type=Path)
    init.add_argument("--name", default="我的桌宠")
    for name, help_text in [("prompts", "Regenerate prompts after editing identity.md"), ("inspect", "Inspect available strips without requiring all states"), ("build", "Assemble all states after geometry checks"), ("preview", "Create an offline animation player"), ("approve", "Record that YOU visually reviewed the current build"), ("install", "Install a reviewed pet without replacing existing pets"), ("package", "Export a reviewed pet as a portable ZIP"), ("demo", "Copy the included generated example into a new project")]:
        action = sub.add_parser(name, help=help_text)
        action.add_argument("project", type=Path)
        if name == "preview":
            action.add_argument("--open", action="store_true", help="Open the offline HTML in your default browser")
        if name in {"install", "package"}:
            action.add_argument("--slug", required=True)
        if name == "install":
            action.add_argument("--pets-dir", type=Path, help="Override CODEX_HOME/pets for testing or a custom installation")
    skill = sub.add_parser("install-skill", help="Install the self-contained Codex skill and runner")
    skill.add_argument("--destination", type=Path, default=codex_home() / "skills/various-pet")
    return command


def run(args: argparse.Namespace) -> int:
    if args.command == "install-skill":
        print(install_skill(args.destination.expanduser().absolute()))
        print("Skill installed. Start a new Codex chat, invoke $various-pet and provide a reference image.")
        return 0
    root = args.project.expanduser().absolute()
    if args.command == "init":
        print(create_project(root, args.name, args.reference))
        print("Next: edit identity.md, upload your reference in your signed-in browser, then follow prompts.md.")
        return 0
    if args.command == "demo":
        print(demo(root))
        print("Next: build, preview, visually review, approve, then install with a new slug.")
        return 0
    config(root)
    if args.command == "prompts":
        from .prompts import generate
        print(generate(root))
    elif args.command in {"inspect", "build"}:
        from .engine import process_project
        if args.command == "build":
            # A failed new attempt must not reuse review of a prior final image.
            child(root, "final/approval.json").unlink(missing_ok=True)
        before = input_digest(root)
        quality = process_project(root, assemble=args.command == "build", previews=True)
        if before != input_digest(root):
            raise ValueError("Sources changed during processing; run again")
        print(json.dumps({key: quality.get(key) for key in ("missing_states", "errors", "geometric_checks_ok", "assembly_ready", "assembled")}, ensure_ascii=False, indent=2))
        if args.command == "build":
            if not quality.get("assembled"):
                return 2
            quality["input_sha256"] = before
            write_json(child(root, "final/quality.json"), quality)
            print(child(root, "final/spritesheet-v1.png"))
        elif quality.get("errors"):
            return 2
    elif args.command == "preview":
        from .preview import render
        destination = render(root)
        print(destination)
        if args.open:
            webbrowser.open(destination.resolve().as_uri())
    elif args.command == "approve":
        _, quality = current_build(root)
        write_json(child(root, "final/approval.json"), {"visually_reviewed": True, "sprite_sha256": quality["output_sha256"], "input_sha256": quality["input_sha256"], "reviewed_at": datetime.now(timezone.utc).isoformat()})
        print("Recorded your visual review of this exact build. This is a human assertion, not automatic art-quality certification.")
    elif args.command == "install":
        print(install_pet(root, args.slug, args.pets_dir))
        print("Installed files. In Codex: Settings → Pets → Refresh → select your pet. Selection is not changed by this command.")
    elif args.command == "package":
        print(package_pet(root, args.slug))
    return 0


def main(argv: list[str] | None = None) -> int:
    # Pet names and project paths may contain characters outside Windows' ANSI code page.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        return run(args)
    except (OSError, ValueError, KeyError, TypeError, Image.DecompressionBombError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
