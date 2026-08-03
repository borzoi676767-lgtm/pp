# Vendored skills

Third-party skills copied into this repo so Claude picks them up automatically
when working here. None of them are part of the Sasquatch Coffee theme — they
only shape how Claude approaches certain kinds of work.

| Set | Skills | Source | Version / commit | Licence |
|---|---|---|---|---|
| Marketing | 49 (`cro`, `copywriting`, `ads`, `emails`, `seo-audit`, …) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | v2.10.0 · `7868cb9` (2026-07-27) | MIT |
| Video | 1 (`watch`) | [bradautomates/claude-video](https://github.com/bradautomates/claude-video) | v0.2.0 · `83da59f` (2026-06-30) | MIT |

## Why vendored instead of installed as plugins

Both upstreams ship as Claude Code plugins, which install under `~/.claude/`.
That is the wrong place here: sessions for this repo run in a throwaway
container that is wiped after a period of inactivity, so a plugin install would
be gone by the next session. Committing the skills to the repo is what makes
them persist — they load for anyone working in this repo with no per-session
setup.

## `watch` — external dependencies

`watch` is the only skill here that runs code rather than just instructing
Claude. It shells out to two binaries that are **not** in the repo and **not**
in the container image:

| Dependency | Install | Needed for |
|---|---|---|
| `ffmpeg` / `ffprobe` | `apt-get install ffmpeg` | frame extraction, audio split |
| `yt-dlp` | `pip install yt-dlp` | downloading remote videos |

Both must be reinstalled in each new session. Local video files work with just
these two; remote URLs also need network access to the host.

A Whisper API key is **optional** — `watch` reads a video's own captions when it
has them, and only falls back to a transcription API when it does not. To enable
the fallback, put `GROQ_API_KEY` or `OPENAI_API_KEY` in `~/.config/watch/.env`
(`chmod 600`). Note that this uploads the video's audio to Groq or OpenAI.

Upstream also ships a `SessionStart` hook that prints a one-line setup-status
message. It is **not** installed here — it depends on `CLAUDE_PLUGIN_ROOT`,
which only exists for real plugin installs, and it is cosmetic. Run
`python3 .claude/skills/watch/scripts/setup.py --check` for the same
information.

## What was left out

- `marketingskills`: the `skills/*/evals/` test fixtures (~420K) and the `tools/`
  directory of ~65 standalone Node CLI wrappers for marketing SaaS APIs, each
  needing its own key.
- `claude-video`: `tests/`, `hooks/`, `dev-sync.sh`, and the Codex plugin
  manifest — none are used at runtime.

## Updating

```sh
# marketing skills
git clone --depth 1 https://github.com/coreyhaines31/marketingskills /tmp/ms
find .claude/skills -mindepth 1 -maxdepth 1 -type d ! -name watch -exec rm -rf {} +
cp -r /tmp/ms/skills/. .claude/skills/
find .claude/skills -type d -name evals -prune -exec rm -rf {} +

# watch
git clone --depth 1 https://github.com/bradautomates/claude-video /tmp/cv
rm -rf .claude/skills/watch && cp -r /tmp/cv/skills/watch .claude/skills/watch
```

Then update the version and commit columns in the table above.
