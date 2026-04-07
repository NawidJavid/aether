# .claude/ — Claude Code project configuration

This folder configures Claude Code for the Aether project. Drop the entire `.claude/` directory in your project root next to `CLAUDE.md`.

## What's in here

```
.claude/
├── settings.json           # Project-shared Claude Code settings (commit this)
├── README.md               # This file
├── commands/
│   └── milestone.md        # /milestone slash command for the milestone workflow
└── rules/
    ├── backend.md          # Loads when working in backend/**
    ├── backend-pipeline.md # Loads when working in backend/src/aether/pipeline/**
    ├── frontend-particle.md # Loads when working in frontend/src/particle/**
    └── frontend-app.md     # Loads when working in frontend/src/components/**, playback/**, etc.
```

## Why path-scoped rules instead of one giant CLAUDE.md

Anthropic's official guidance is that CLAUDE.md files over ~200 lines (or roughly 40KB) **measurably reduce how reliably Claude follows the instructions**. Bigger isn't better — the longer the file, the worse the adherence and the more context it consumes on every session start.

The fix is path-scoped rules: detailed implementation guidance for each area lives in its own file under `.claude/rules/`, with a `paths:` frontmatter block specifying which directories it applies to. **Rules only load into context when Claude reads files in matching directories.** This means:

- The lean `CLAUDE.md` (~10KB) is always loaded — it contains the project overview, principles, build order, and commands
- When Claude reads a file in `backend/`, the backend rules attach themselves
- When Claude reads a file in `frontend/src/particle/`, the particle rules attach themselves
- When Claude is working on the frontend, it doesn't waste context on backend implementation details, and vice versa

The total content is roughly the same, but only ~10KB loads at session start instead of the full 60KB+.

You can verify what's loaded in any session by running `/memory` inside Claude Code.

## settings.json

The shared project settings. Commit this to git so anyone cloning the repo gets the same Claude Code configuration. Key choices:

- **`plansDirectory: "./plans"`** — Plans created in Plan Mode are saved to `./plans/` in the project root rather than `~/.claude/plans/`. This means they're version-controlled and survive context compaction. After each milestone you'll have a permanent record of what was built and why. Commit them.
- **`effortLevel: "high"`** — Bumps Opus 4.6's reasoning depth from the new default of "medium" to "high".
- **`alwaysThinkingEnabled` and `showThinkingSummaries`** — Always show Claude's reasoning. Useful for catching misunderstandings early in the planning phase.
- **`permissions.allow`** — Pre-approves common dev commands so you don't get prompted dozens of times per session. **Heads up:** there's an open Claude Code bug (#18846, #13340) where bash permission rules in settings.json are not always honored. You may still see prompts even for commands on this list. Approve them as they come up — over time they'll be silenced for the session.
- **`permissions.deny`** — Blocks reads of `.env` files and any file under `backend/data/` (which may contain cached API responses or generated content). Also blocks `sudo`, `rm -rf /`, and arbitrary external curl. These deny rules work more reliably than allow rules.

If you want personal settings that override or extend these without committing them, create `.claude/settings.local.json` — Claude Code automatically gitignores `*.local.json` files.

## commands/milestone.md

Defines the `/milestone` slash command. Usage:

```
/milestone 0      # plan and execute Milestone 0
/milestone 1      # plan and execute Milestone 1 (with ultrathink for the aesthetic gate)
/milestone 2      # ... and so on through 6
```

The command:

1. Tells Claude to read CLAUDE.md and which rule files matter for this milestone
2. Provides milestone-specific guidance (goal, constraints, deliverable check)
3. Forces a plan-first workflow with an explicit stop point before any code is written
4. Stops at the end of each milestone instead of sprinting into the next

For Milestones 0 and 1 the rule files have to be loaded manually because there are no project files yet to trigger auto-loading. From Milestone 2 onward, Claude reads existing project files during planning, which auto-loads the relevant rules.

## rules/

Path-scoped implementation guidance. The `paths:` frontmatter at the top of each file specifies which directories it applies to. You don't need to manually load these in normal use — Claude Code loads them automatically when reading matching files.

If you ever want to read or edit them directly, they're plain markdown.

## The recommended workflow per milestone

```bash
# In the project root
cd aether/

# Open Claude Code
claude

# Inside the Claude Code REPL:
/plan                  # enter plan mode (read-only, no edits)
/milestone 0           # kick off Milestone 0

# Claude reads CLAUDE.md, the relevant rules, examines files, produces a plan
# You review the plan, edit with Ctrl+G if needed
# When happy, approve the plan

# Claude exits plan mode and executes
# When done, Claude reports status and stops

# Verify the milestone deliverable manually

# When you're satisfied, commit
git add -A && git commit -m "milestone 0: project skeleton"

# Clear the session and start fresh for the next milestone
/clear
/plan
/milestone 1
```

The `/clear` between milestones is important — don't try to do all 6 milestones in one Claude Code session. Context will compact, plans will get lost, and quality drops. Each milestone gets its own clean session.

## Windows note

You're on Windows. The Shift+Tab shortcut to enter plan mode has known bugs on Windows in Claude Code v2.1.3 and later. **Always use the `/plan` slash command instead** — it works reliably on every platform and version. The `/milestone` command is platform-independent.

## Verifying the rules are loading

After Claude Code starts in your project, run `/memory` inside the session. You should see:

- CLAUDE.md loaded
- Any unconditional rules loaded (none in our case — all rules have `paths:` frontmatter)

After Claude reads its first backend file in a session, run `/memory` again. You should now also see `backend.md` loaded. This is how you confirm the path-scoped mechanism is working.

## When NOT to use /milestone

`/milestone` is for the structured build phase. For one-off questions, debugging, or tweaks, just talk to Claude Code normally without the slash command. Save the structured workflow for the actual milestone work.
