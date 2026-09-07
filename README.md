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
