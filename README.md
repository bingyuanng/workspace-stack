# Workspace stack

Personal preferences and reusable skills for OpenCode, Codex, and Claude Code.
Requires Python 3.9+ and directory symlink support; use WSL on Windows if needed.

## Install

Clone or copy this project to a permanent folder, then run from the checkout:

```sh
# Preview changes
python3 scripts/install.py --harness opencode

# Install
python3 scripts/install.py --harness opencode --apply
```

Use `--harness codex` or `--harness claude` for those tools. For other harnesses,
use `--harness custom` with `--instructions-file` and `--skills-dir` pointing to
locations that harness supports. Run `python3 scripts/install.py --help` for options.

Start a new harness session after installation. Provider login stays unchanged.

## How it works

- `preferences/*.md` contains short global defaults and tells the agent when to
  read skills. The installer copies these into a marked section of the harness's
  global instruction file.
- `skills/<name>/SKILL.md` contains detailed topic guidance. Each skill is linked
  into the harness's global skills directory.
- Writing applies before final responses. Testing applies to behavior changes,
  bug fixes, and test design or review. Other skills load when relevant.

Existing instructions outside the marked section and unrelated skills are
preserved. Instruction changes get a backup beside the original file.
Installation stops on skill conflicts or if OpenCode would hide an existing
Claude instruction fallback. Resolve the reported conflict before retrying.

## Update or remove

After changing preferences or adding skills, rerun installation for each harness.
Edits to existing skills are available through their links. Start a new session
so the harness refreshes its instructions.

To remove the managed instructions and this checkout's skill links:

```sh
python3 scripts/install.py --harness opencode --remove --apply
```

Uninstall before moving the checkout or deleting skill folders, then reinstall
from the new location. Existing user content and backups remain.

## Test

```sh
python3 -m unittest discover -s tests -v
```

Tests use temporary homes and leave your live configuration unchanged.
