# agentignore

A Claude Code plugin that prevents the agent from reading or editing files matching patterns in a `.agentignore` file — just like `.gitignore`, but for AI agents.

## Installation

### Via plugin system

Add the marketplace from GitHub, then install:

```shell
/plugin marketplace add https://github.com/devias-io/claude-plugins
/plugin install agentignore@devias
```

To test locally without installing:

```shell
claude --plugin-dir ./plugins/agentignore
```

### Manual (settings.json)

Clone the repo, then add the hook to your project's `.claude/settings.json` (or `~/.claude/settings.json` for all projects):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/claude-plugins/plugins/agentignore/hooks/agentignore.py"
          }
        ]
      }
    ]
  }
}
```

Replace `/path/to/claude-plugins` with the absolute path to your clone.

## Usage

Create a `.agentignore` file in your project root:

```gitignore
# Secrets & credentials
.env
.env.*
*.pem
*.key
secrets/

# Sensitive config
config/production.yml

# Personal notes
NOTES.md
```

Claude Code will refuse to read, edit, or write any file matched by these patterns. It will see a message explaining why the file is blocked so it can adjust its approach.

The `.agentignore` file is picked up automatically — no configuration needed beyond creating it.

## Pattern syntax

Patterns follow [gitignore rules](https://git-scm.com/docs/gitignore#_pattern_format):

| Pattern | Matches |
|---------|---------|
| `*.env` | Any file ending in `.env`, anywhere in the tree |
| `.env` | A file named exactly `.env`, anywhere in the tree |
| `secrets/` | A directory named `secrets` and everything inside it |
| `**/secrets/**` | A `secrets` directory at any depth |
| `/config/prod.yml` | Only `config/prod.yml` at the project root (leading `/` anchors) |
| `config/prod.yml` | `config/prod.yml` relative to the `.agentignore` location |
| `!secrets/public.pem` | Un-ignores this file even if a broader pattern matched it |
| `# comment` | Ignored line |

Patterns are relative to the directory containing `.agentignore`. You can place `.agentignore` files in subdirectories — Claude uses the nearest one found when walking up from the target file.

> **Note:** Only one `.agentignore` is consulted per file access — the closest ancestor. Unlike git, parent-directory `.agentignore` files are not merged. To protect the whole project, place a single `.agentignore` at the root.

## Which tools are blocked

The hook intercepts these Claude Code tools before they execute:

- `Read`
- `Edit`
- `Write`

Shell commands run via the `Bash` tool (e.g. `cat`, `grep`) are not intercepted.

## Requirements

- Claude Code with plugin support
- Python 3 (pre-installed on macOS and most Linux distributions — no pip packages required)
