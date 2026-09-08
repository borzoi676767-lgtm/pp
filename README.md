# pp
aliens

## Skills

- `.claude/skills/kronos` — forecast OHLCV candlesticks with [Kronos](https://github.com/shiyu-coder/Kronos).
  Run `python .claude/skills/kronos/scripts/setup_kronos.py` once to install the model code.
- `.claude/skills/freqtrade` — build, backtest and validate trading strategies with
  [Freqtrade](https://github.com/freqtrade/freqtrade).
  Run `python .claude/skills/freqtrade/scripts/setup_freqtrade.py` once to install it.
- `.claude/skills/ollama` — run open-weight LLMs locally with
  [Ollama](https://github.com/ollama/ollama).
  Run `bash .claude/skills/ollama/scripts/setup_ollama.sh` once to install it.

### UI, animation and design engineering

Twelve skills from [emilkowalski/skills](https://github.com/emilkowalski/skills) (MIT),
installed as authored — no setup step, they work as soon as they're on disk.

- `emil-design-eng` — the main design-engineering philosophy skill
- `animate`, `animate-expo` — build an animation with the right curve, duration and properties
- `review-animations`, `improve-animations`, `find-animation-opportunities` — audit and improve existing motion
- `animation-vocabulary` — the words that get you the animation you meant
- `apple-design`, `pick-ui-library`, `prototype`, `write-swift`, `ask-sonner`

`pick-ui-library`, `prototype` and `review-animations` are user-invoked only
(`disable-model-invocation`); the rest trigger automatically.

### Design review and polish

- `.claude/skills/impeccable` — [Impeccable](https://github.com/pbakaus/impeccable) (Apache 2.0),
  a frontend design skill with 23 commands (`/impeccable init`, `polish`, `audit`, `critique`,
  `animate`, ...) and 61 deterministic detector rules.

Installed with its four subagents (`.claude/agents/impeccable-*.md`) and `.claude/settings.json`,
which registers two hooks: a fast check after every `Edit`/`Write`, and a deeper pass on `Stop`.
Both shell out to `.claude/skills/impeccable/scripts/impeccable`, a launcher that downloads a
checksum-verified engine binary to `~/.impeccable/bin/` on first run and no-ops if the script is
absent. Remove `.claude/settings.json` to disable the hooks while keeping the skill.

### Trading and market research

Seventy-four skills from
[tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills)
(MIT) — screeners (CANSLIM, VCP, PEAD, dividend growth, Finviz), market-regime and breadth
analysis, backtesting, position sizing, risk gates, and edge-research pipelines.

Most require API keys before they do anything useful:

```bash
export FMP_API_KEY=...        # Financial Modeling Prep, free tier 250 req/day — used by most skills
export FINVIZ_API_KEY=...     # FINVIZ Elite, paid — dividend/pre-screening only
export ALPACA_API_KEY=...     # Alpaca, paper trading is free — portfolio-manager only
```

Upstream is explicit that this is for research and education, not financial advice, and
`portfolio-manager` reaches a broker only through an Alpaca MCP server you configure
yourself. Nothing here places an order on its own.

These add roughly 7,600 tokens of always-on context. The upstream README supports installing
individual skill folders — delete the ones you don't want from `.claude/skills/` to trim.

- `.claude/skills/design-taste-frontend` — [taste-skill](https://github.com/Leonxlnx/taste-skill)
  (MIT), an anti-slop frontend skill for landing pages, portfolios and redesigns. Installed with
  `npx skills add`, which recorded `skills-lock.json` (source + content hash).

## MCP servers

`.mcp.json` registers the [21st.dev](https://21st.dev) component MCP server at project
scope. It stores `${API_KEY_21ST}` as an environment-variable reference, not the key
itself, so nothing secret is committed.

To use it:

```bash
export API_KEY_21ST=<your 21st.dev key>   # from https://21st.dev
claude                                     # approve the project MCP server when prompted
```

Project-scoped MCP servers require explicit approval on first use, and the key must be
present in the environment before starting Claude Code — `claude mcp get 21st` warns if
it is missing.
