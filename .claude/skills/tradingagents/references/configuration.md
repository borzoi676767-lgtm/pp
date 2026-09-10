# Configuring TradingAgents

Contents: [Providers](#llm-providers) · [Models](#model-roles) · [Env overrides](#environment-overrides) · [Data vendors](#data-vendors) · [Cost keys](#keys-that-drive-cost) · [Paths](#paths-and-state) · [Troubleshooting](#troubleshooting)

Config is a plain dict. Start from `DEFAULT_CONFIG` and override:

```python
from tradingagents.default_config import DEFAULT_CONFIG
config = DEFAULT_CONFIG.copy()
config["max_debate_rounds"] = 2
```

## LLM providers

Set `llm_provider`. The package's canonical provider → key mapping lives in
`tradingagents/llm_clients/api_key_env.py` — read it rather than guessing, because the
provider names are not the obvious ones:

| Provider | Key env |
| --- | --- |
| `openai` | `OPENAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |
| `google` | `GOOGLE_API_KEY` |
| `azure` | `AZURE_OPENAI_API_KEY` |
| `bedrock` | *none* — AWS credential chain |
| `ollama` | *none* — local |
| `glm` / `glm-cn` | `ZHIPU_API_KEY` / `ZHIPU_CN_API_KEY` |
| `qwen` / `qwen-cn` | `DASHSCOPE_API_KEY` / `DASHSCOPE_CN_API_KEY` |
| `minimax` / `minimax-cn` | `MINIMAX_API_KEY` / `MINIMAX_CN_API_KEY` |
| `xai`, `deepseek`, `openrouter`, `mistral`, `kimi`, `groq`, `nvidia` | `<NAME>_API_KEY` (kimi → `MOONSHOT_API_KEY`) |
| `openai_compatible` | `OPENAI_COMPATIBLE_API_KEY` (optional — keyless local relays work) |

Note the China-region variants are separate accounts; keys are not interchangeable.
`backend_url` overrides the endpoint; leave it `None` to use each provider's default. A
stale provider-specific `backend_url` is a classic misconfiguration — an OpenAI `/v1` left
in place while switching to Gemini produces malformed request URLs.

## Model roles

Two models, used for different work:

- **`quick_think_llm`** — analysts and debaters. This does most of the calls; point it at
  something cheap.
- **`deep_think_llm`** — research manager, portfolio manager. Few calls, so a strong model
  here costs comparatively little.

Reasoning knobs, all `None` (provider default) unless set: `openai_reasoning_effort`,
`anthropic_effort`, `google_thinking_level`, plus `temperature`, `max_tokens`,
`llm_max_retries`.

## Environment overrides

Every important key is settable without touching code:

```
TRADINGAGENTS_LLM_PROVIDER      TRADINGAGENTS_DEEP_THINK_LLM
TRADINGAGENTS_QUICK_THINK_LLM   TRADINGAGENTS_LLM_BACKEND_URL
TRADINGAGENTS_MAX_DEBATE_ROUNDS TRADINGAGENTS_MAX_RISK_ROUNDS
TRADINGAGENTS_TEMPERATURE       TRADINGAGENTS_MAX_TOKENS
TRADINGAGENTS_LLM_MAX_RETRIES   TRADINGAGENTS_CHECKPOINT_ENABLED
TRADINGAGENTS_OUTPUT_LANGUAGE   TRADINGAGENTS_BENCHMARK_TICKER
TRADINGAGENTS_RESULTS_DIR       TRADINGAGENTS_CACHE_DIR
TRADINGAGENTS_GOOGLE_THINKING_LEVEL  TRADINGAGENTS_OPENAI_REASONING_EFFORT
TRADINGAGENTS_ANTHROPIC_EFFORT
```

Values are coerced to the type of the existing default, and an invalid one (`treu` for a
boolean, a non-numeric int) **raises at startup** rather than silently falling back. That is
deliberate — an unattended run should fail loudly, not quietly misconfigure itself.

## Data vendors

```python
config["data_vendors"] = {
    "core_stock_apis":     "yfinance",    # or alpha_vantage
    "technical_indicators":"yfinance",
    "fundamental_data":    "yfinance",
    "news_data":           "yfinance",
    "macro_data":          "fred",        # needs FRED_API_KEY
    "prediction_markets":  "polymarket",  # keyless
}
```

The configured value is the **exact chain** — requests are not silently routed to vendors
you did not pick. Comma-separate for ordered fallback (`"yfinance,alpha_vantage"`), or use
`"default"` for all available. `tool_vendors` overrides individual tools above the category.

Defaults are keyless apart from `fred`, so an LLM key alone is enough to run.

## Keys that drive cost

`selected_analysts` (constructor arg, not config) · `max_debate_rounds` ·
`max_risk_discuss_rounds` · `quick_think_llm` · `max_tokens`. See the skill's cost table.

`news_article_limit` (20), `global_news_article_limit` (10) and `global_news_lookback_days`
(7) control how much text enters analyst prompts — lowering them cuts input tokens
noticeably.

## Paths and state

Everything lives under `~/.tradingagents/`: `logs/` (results), `cache/` (data),
`memory/trading_memory.md` (the reflection log). `memory_log_max_entries` caps the log,
pruning oldest *resolved* entries only; pending ones are never pruned.

`checkpoint_enabled: True` makes LangGraph persist state per node, so a crashed run resumes
rather than re-paying for the whole pipeline. Worth enabling for anything batch or long.

`reflect_and_remember(returns)` feeds realized P&L back into memory. `benchmark_ticker` (or
`benchmark_map`, which picks a regional index from the ticker suffix — `.T` → Nikkei, `.L` →
FTSE) sets what alpha is measured against; US tickers default to SPY.

## Troubleshooting

- **Every call fails instantly** — provider key missing or wrong variable. Run `preflight.py`.
- **Malformed request URLs after switching provider** — stale `backend_url`; set it to `None`.
- **Run hangs or trips a gateway timeout** — a model emitting unbounded reasoning. Set
  `max_tokens`.
- **Bursty 429s aborting runs** — raise `llm_max_retries`.
- **Different answer each run** — expected. LLM sampling; `temperature` reduces but does not
  remove it, and reasoning models largely ignore it.
