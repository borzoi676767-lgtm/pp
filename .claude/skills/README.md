# Vendored skills

Third-party skills copied into this repo so Claude picks them up automatically
when working here. None of them are part of the Sasquatch Coffee theme — they
only shape how Claude approaches certain kinds of work.

| Set | Skills | Source | Version / commit | Licence |
|---|---|---|---|---|
| Marketing | 49 (`cro`, `copywriting`, `ads`, `emails`, `seo-audit`, …) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | v2.10.0 · `7868cb9` (2026-07-27) | MIT |
| Video | 1 (`watch`) | [bradautomates/claude-video](https://github.com/bradautomates/claude-video) | v0.2.0 · `83da59f` (2026-06-30) | MIT |
| UI/UX | 7 (`ui-ux-pro-max`, `ui-styling`, `design`, `design-system`, `brand`, `slides`, `banner-design`) | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | v2.11.0 · `14ddef5` (2026-08-01) | MIT |

## Why vendored instead of installed as plugins

All three upstreams ship as plugins, which install under `~/.claude/`.
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

## `ui-ux-pro-max` and friends

Seven skills built around CSV databases of styles, palettes, font pairings,
charts and per-stack guidelines, queried through
`.claude/skills/ui-ux-pro-max/scripts/search.py`. Python is stdlib-only, so the
search works with no setup:

```sh
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "dark editorial" -d style
```

A few of the helper scripts shell out, but only to fixed commands — `npx shadcn
add <components>` in `ui-styling`, and `node generate-tokens.cjs` in `brand`.
Those two need Node; everything else does not.

`ui-styling/canvas-fonts/` is 5.5M of TTFs and accounts for most of the size
here. They are kept because `references/canvas-design-system.md` tells the skill
to search that directory — delete them and that path breaks.

Upstream's documented install is `npx ui-ux-pro-max-cli init`. That was **not**
used: it fetches and runs a CLI at install time, and it would write into
`~/.claude/`, which does not survive this container. Copying the skill
directories in is equivalent and inspectable.

## What was left out

- `marketingskills`: the `skills/*/evals/` test fixtures (~420K) and the `tools/`
  directory of ~65 standalone Node CLI wrappers for marketing SaaS APIs, each
  needing its own key.
- `claude-video`: `tests/`, `hooks/`, `dev-sync.sh`, and the Codex plugin
  manifest — none are used at runtime.
- `ui-ux-pro-max-skill`: the repo's `cli/`, `gallery/`, `screenshots/`,
  `preview/`, `projects/`, `src/` and `stack/` trees (~10M of website and CLI
  assets), plus each skill's `scripts/tests/` suites and coverage files.

## Updating

Each set updates independently — none of these commands touch the others.

```sh
# marketing skills (49)
git clone --depth 1 https://github.com/coreyhaines31/marketingskills /tmp/ms
for s in /tmp/ms/skills/*/; do
  n=$(basename "$s"); rm -rf ".claude/skills/$n"; cp -r "$s" ".claude/skills/$n"
done
find .claude/skills -type d -name evals -prune -exec rm -rf {} +

# watch (1)
git clone --depth 1 https://github.com/bradautomates/claude-video /tmp/cv
rm -rf .claude/skills/watch && cp -r /tmp/cv/skills/watch .claude/skills/watch

# ui/ux (7)
git clone --depth 1 https://github.com/nextlevelbuilder/ui-ux-pro-max-skill /tmp/ux
for n in ui-ux-pro-max design-system design brand slides banner-design ui-styling; do
  rm -rf ".claude/skills/$n"; cp -r "/tmp/ux/.claude/skills/$n" ".claude/skills/$n"
done
find .claude/skills -path "*/scripts/tests" -prune -exec rm -rf {} +
```

Then update the version and commit columns in the table above.
