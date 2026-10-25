# Workspace stack

Portable personal instructions and skills for local coding agents. Keep this
checkout in a permanent location on each computer. The installer adds preferences
to the harness's global instructions and links each skill into its discovery
directory. Python 3.9 or newer is required; no packages are needed.

## Set up a new computer

Clone or copy this project to a permanent directory, then run these commands from
the checkout:

```sh
python3 scripts/install.py --harness opencode
python3 scripts/install.py --harness opencode --apply
```

The first command previews changes. The second installs them. Start a new
OpenCode session in any project afterward.

Provider login is separate from these local files. This installer does not change
models, subscriptions, credentials, permissions, plugins, or harness settings.

To check loading, ask in a new session:

> Identify the global preferences you loaded and the path of the general-writing
> skill. Read that skill before answering.

Skill discovery makes descriptions available; it does not load every skill's
body. The installed preferences instruct the agent to read general-writing before
each final response and testing when changing behavior, fixing bugs, or designing
and reviewing tests. Other skills remain available when relevant. This relies on
the agent following instructions and having file access;
the installer does not bypass disabled skills or managed policies.

## Other harnesses

```sh
python3 scripts/install.py --harness codex --apply
python3 scripts/install.py --harness claude --apply
```

Built-in destinations:

- OpenCode: `~/.config/opencode/AGENTS.md` and `~/.config/opencode/skills/`.
- Codex: `~/.codex/AGENTS.md` and `~/.agents/skills/`. If a nonempty global
  `AGENTS.override.md` is active, its managed section is updated instead.
- Claude Code: `~/.claude/CLAUDE.md` and `~/.claude/skills/`.

The adapters honor `XDG_CONFIG_HOME`, `CODEX_HOME`, and `CLAUDE_CONFIG_DIR` for
their respective paths. For another harness, confirm its documented global
instruction and skill locations, then provide both:

```sh
python3 scripts/install.py --harness custom \
  --instructions-file "$HOME/.other-agent/AGENTS.md" \
  --skills-dir "$HOME/.other-agent/skills" \
  --apply
```

Custom mode supports harnesses that load a plain Markdown instruction file and
Agent Skills directories. It cannot make an unsupported harness discover skills.
It checks collisions in the supplied skill directory; built-in adapters also
check their known global compatibility directories. Project-local overrides and
skills must still be reviewed in the project where you work.

## Keep existing configuration

The installer preserves bytes outside its `workspace-stack` markers, backs up an
instruction file before changing it, and updates only its own section on reruns.
Backups are stored beside the original file as
`<filename>.workspace-stack.<timestamp>.bak`.

Skills are linked individually. Existing files, directories, and unrelated links
are retained. A conflicting skill name stops installation before any changes;
choose which version to keep explicitly. There is no force-overwrite option.

If creating OpenCode's global `AGENTS.md` would hide an existing
`~/.claude/CLAUDE.md` fallback, installation stops. Integrate the existing rules
into OpenCode's global file yourself, or use custom mode targeting the active
fallback file and OpenCode's skill directory. The latter adds preferences to a
file shared with Claude Code too.

Existing instruction-file symlinks remain symlinks. A symlink for the entire
destination skill directory is rejected to avoid modifying another skill store.

These are additive personal defaults. They do not grant precedence over current
requests, project requirements, or harness policy, and they cannot automatically
reconcile contradictory instructions.

## Maintain the stack

- Put global preferences in `preferences/*.md`; files are included in filename
  order. `{{STACK_ROOT}}` expands to this checkout's absolute path.
- Keep preferences short: broad defaults and instructions for when to load skills.
  Put detailed topic guidance in skills so it is read only for relevant work.
- Keep each skill in `skills/<name>/SKILL.md`, with matching frontmatter `name`.
- After pulling or editing preferences, rerun the installer for each harness.
  Existing linked skills use the checkout's current content. New skills need an
  installer rerun. Restart the harness to refresh its loaded instructions.
- Before moving the checkout, uninstall from its old location, move it, and
  reinstall. Links and embedded paths depend on its location.

Installation uses directory symlinks. On Windows, use WSL or enable the symlink
privileges required by your Python installation. A symlink failure leaves the
instruction file unchanged.

## Remove an installation

```sh
python3 scripts/install.py --harness opencode --remove
python3 scripts/install.py --harness opencode --remove --apply
```

Removal deletes only the managed section and skill links pointing to this
checkout. It retains user additions and replacement skills. If the installer
created the instruction file and it has no other content, removal deletes it.
Backups remain. Run removal before deleting or renaming skill folders so their
links can still be identified. Use the same harness and path options as install.

## Verify the installer

```sh
python3 -m unittest discover -s tests -v
```

Tests use temporary homes and do not change your live agent configuration.

The adapters follow the official documentation for
[OpenCode instructions](https://opencode.ai/docs/rules/) and
[skills](https://opencode.ai/docs/skills/),
[Codex instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
and [skills](https://learn.chatgpt.com/docs/build-skills), and
[Claude Code instructions](https://code.claude.com/docs/en/memory) and
[skills](https://code.claude.com/docs/en/skills).
