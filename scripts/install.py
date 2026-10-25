#!/usr/bin/env python3
"""Add this checkout's preferences and skills to a local agent harness."""

import argparse
from datetime import datetime, timezone
import difflib
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
START = "<!-- workspace-stack:begin -->"
END = "<!-- workspace-stack:end -->"


def present(path):
    return path.exists() or path.is_symlink()


def read(path):
    if path.is_symlink() and not path.exists():
        raise ValueError(f"Broken instruction symlink: {path}")
    return path.read_bytes() if path.exists() else b""


def paths(args):
    home = Path.home()
    config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    claude = Path(os.environ.get("CLAUDE_CONFIG_DIR", home / ".claude"))
    codex = Path(os.environ.get("CODEX_HOME", home / ".codex"))
    if args.harness == "opencode":
        instructions = config / "opencode/AGENTS.md"
        skills = config / "opencode/skills"
        search = [skills, home / ".agents/skills", claude / "skills"]
        fallback = claude / "CLAUDE.md"
        if not present(instructions) and present(fallback) and not args.remove:
            raise ValueError(
                f"Creating {instructions} would hide existing fallback {fallback}. "
                "Integrate those instructions into OpenCode explicitly first, "
                "or use --harness custom with the active instruction and skill paths."
            )
    elif args.harness == "codex":
        override = codex / "AGENTS.override.md"
        instructions = override if read(override).strip() else codex / "AGENTS.md"
        skills = home / ".agents/skills"
        search = [skills, codex / "skills"]
    elif args.harness == "claude":
        instructions = claude / "CLAUDE.md"
        skills = claude / "skills"
        search = [skills]
    else:
        if not args.instructions_file or not args.skills_dir:
            raise ValueError("custom requires --instructions-file and --skills-dir")
        instructions = Path(args.instructions_file).expanduser().absolute()
        skills = Path(args.skills_dir).expanduser().absolute()
        search = [skills]
    if args.harness != "custom" and (args.instructions_file or args.skills_dir):
        raise ValueError("Path overrides require --harness custom")
    # A directory-wide link would expose every skill to another checkout.
    if skills.is_symlink():
        raise ValueError(f"Skill directory is a symlink; use its owner to manage it: {skills}")
    return instructions, skills, search


def block_span(data):
    start, end = START.encode(), END.encode()
    if data.count(start) != data.count(end) or data.count(start) > 1:
        raise ValueError("Malformed or duplicate workspace-stack markers; repair them first")
    if start not in data:
        return None
    first = data.index(start)
    last = data.index(end) + len(end)
    if first >= last - len(end):
        raise ValueError("workspace-stack markers are out of order")
    return first, last


def render_preferences():
    files = sorted((ROOT / "preferences").glob("*.md"))
    if not files:
        raise ValueError("No preferences/*.md files found")
    text = "\n\n".join(p.read_text(encoding="utf-8").strip() for p in files)
    if START in text or END in text:
        raise ValueError("Preference files must not contain installer markers")
    return text.replace("{{STACK_ROOT}}", ROOT.as_posix())


def skill_sources():
    sources = sorted(p.parent for p in (ROOT / "skills").glob("*/SKILL.md"))
    for source in sources:
        text = (source / "SKILL.md").read_text(encoding="utf-8")
        match = re.search(r"^name:\s*['\"]?([a-z0-9-]+)['\"]?\s*$", text, re.M)
        if not match or match.group(1) != source.name:
            raise ValueError(f"Skill name must match its directory: {source}")
    return sources


def same_link(path, source):
    return path.is_symlink() and path.resolve() == source.resolve()


def conflicts(sources, destination, search):
    errors = []
    for source in sources:
        target = destination / source.name
        if present(target) and not same_link(target, source):
            errors.append(f"Existing skill left untouched: {target}")
        for directory in dict.fromkeys(search):
            if not directory.exists():
                continue
            # glob follows direct skill-directory links; rglob alone skips them.
            manifests = set(directory.glob("*/SKILL.md")) | set(directory.rglob("SKILL.md"))
            candidate = directory / source.name
            if present(candidate) and candidate != target and not same_link(candidate, source):
                errors.append(f"Same skill directory already available: {candidate}")
            for manifest in manifests:
                if manifest.resolve() == (source / "SKILL.md").resolve():
                    continue
                text = manifest.read_text(encoding="utf-8")
                match = re.search(r"^name:\s*['\"]?([a-z0-9-]+)['\"]?\s*$", text, re.M)
                if match and match.group(1) == source.name:
                    errors.append(f"Same skill name already available: {manifest}")
    return sorted(set(errors))


def install(args):
    instructions, skills, search = paths(args)
    original = read(instructions)
    span = block_span(original)
    sources = skill_sources()
    # Keep enough ownership information to restore original bytes on removal.
    separator, created_file = 0, not present(instructions)
    if span:
        metadata = re.search(rb"<!-- workspace-stack:separator=(\d);created=([01]) -->", original[span[0]:span[1]])
        if metadata:
            separator, created_file = int(metadata[1]), bool(int(metadata[2]))
    if args.remove:
        if span and original[max(0, span[0] - separator):span[0]] != b"\n" * separator:
            raise ValueError("Managed separator was edited; repair the markers before removal")
        updated = original if span is None else original[:span[0] - separator] + original[span[1]:]
    else:
        collisions = conflicts(sources, skills, search)
        if collisions:
            raise ValueError("\n".join(collisions) + "\nNo changes made. Resolve the name conflict explicitly.")
        if not span:
            separator = 2 if original else 0
        block = (
            f"{START}\n<!-- workspace-stack:separator={separator};created={int(created_file)} -->\n"
            f"{render_preferences()}\n{END}"
        ).encode()
        if span:
            updated = original[:span[0]] + block + original[span[1]:]
        else:
            updated = original + b"\n" * separator + block

    print(f"{'REMOVE' if args.remove else 'INSTALL'} {args.harness} from {ROOT}")
    print(f"{'UPDATE' if updated != original else 'KEEP'} instructions: {instructions}")
    changes = []
    for source in sources:
        target = skills / source.name
        if args.remove:
            action = "UNLINK" if same_link(target, source) else "KEEP"
        else:
            action = "KEEP" if same_link(target, source) else "LINK"
        print(f"{action} skill: {target} -> {source}")
        if action != "KEEP":
            changes.append((action, target, source))
    if updated != original:
        print("--- instruction changes ---")
        print("".join(difflib.unified_diff(
            original.decode("utf-8").splitlines(keepends=True),
            updated.decode("utf-8").splitlines(keepends=True),
            fromfile=str(instructions), tofile=str(instructions),
        )))
    if not args.apply:
        print("Preview only. Add --apply to write these changes.")
        return

    # Link first: a symlink-permission failure must not change instructions.
    created = []
    try:
        for action, target, source in changes:
            if action == "LINK":
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(source, target_is_directory=True)
                created.append(target)
        if updated != original:
            # Follow an existing file symlink without replacing the link itself.
            output = instructions.resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                backup = output.with_name(f"{output.name}.workspace-stack.{stamp}.bak")
                shutil.copy2(output, backup)
                print(f"BACKUP {backup}")
            if args.remove and created_file and not updated and not instructions.is_symlink():
                output.unlink()
            else:
                # Replace the resolved file atomically while preserving its mode.
                fd, temp_name = tempfile.mkstemp(prefix=".workspace-stack-", dir=output.parent)
                try:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(updated)
                    if output.exists():
                        shutil.copymode(output, temp_name)
                    os.replace(temp_name, output)
                finally:
                    if os.path.exists(temp_name):
                        os.unlink(temp_name)
        for action, target, source in changes:
            if action == "UNLINK" and same_link(target, source):
                target.unlink()
    except Exception:
        for target in reversed(created):
            if same_link(target, ROOT / "skills" / target.name):
                target.unlink()
        raise
    print("Done. Start a new harness session to load the instructions.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", choices=["opencode", "codex", "claude", "custom"], required=True)
    parser.add_argument("--instructions-file", help="Global instruction file for a custom harness")
    parser.add_argument("--skills-dir", help="Global skill directory for a custom harness")
    parser.add_argument("--apply", action="store_true", help="Write changes; default is preview only")
    parser.add_argument("--remove", action="store_true", help="Remove the managed block and this checkout's skill links")
    args = parser.parse_args()
    try:
        install(args)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
