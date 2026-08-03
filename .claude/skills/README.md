# Vendored marketing skills

These 49 skills are third-party, copied from **coreyhaines31/marketingskills**
(MIT licence). They are not part of the Sasquatch Coffee theme — they only tell
Claude how to approach marketing work in this repo.

| | |
|---|---|
| Source | https://github.com/coreyhaines31/marketingskills |
| Plugin | `marketing-skills` v2.10.0 |
| Commit | `7868cb9251fad80a73d26e488a5ad5f6c4a9f335` (2026-07-27) |
| Author | Corey Haines |
| Licence | MIT |

## Why vendored instead of installed as a plugin

Claude Code sessions for this repo run in a throwaway container that is wiped
after a period of inactivity, so anything under `~/.claude/` is gone by the next
session. Committing the skills here is what makes them survive — they load
automatically for anyone working in this repo, with no per-session setup.

## What was left out

The upstream `skills/*/evals/` directories (test fixtures, ~420K) are not
copied — they are for validating the skills, not for running them. Upstream's
`tools/` directory is also not copied; it holds standalone Node CLI wrappers for
~65 marketing SaaS APIs, each of which needs its own API key.

## Updating

```sh
git clone --depth 1 https://github.com/coreyhaines31/marketingskills /tmp/ms
rm -rf .claude/skills/*/                       # keeps this README
cp -r /tmp/ms/skills/. .claude/skills/
find .claude/skills -type d -name evals -prune -exec rm -rf {} +
```

Then update the commit and version in the table above.
