---
name: tradingagents
description: Run TradingAgents (github.com/TauricResearch/TradingAgents), a multi-agent LLM framework where analyst, researcher, trader and risk agents debate a ticker and emit a BUY/SELL/HOLD decision with reports. Use when the user mentions TradingAgents or TauricResearch, wants an LLM agent debate or multi-agent analysis of a stock, asks to run bull-vs-bear research on a ticker, wants the framework's analyst/researcher/risk-manager pipeline, or needs help configuring its LLM providers, data vendors, debate rounds or costs. Also use when a TradingAgents run is expensive, slow, hanging, or producing decisions the user does not trust.
---

# TradingAgents

A LangGraph pipeline where specialized LLM agents analyze a ticker and argue toward a
decision: analysts gather evidence, a bull and a bear debate it, a research manager rules,
a trader proposes, three risk agents argue the risk, and a portfolio manager decides.

```
Market ─┐
Social ─┤                    ┌─ Aggressive ─┐
News   ─┼→ Bull ⇄ Bear → Research → Trader →┼─ Neutral ────┼→ Portfolio → BUY/SELL/HOLD
Fundam ─┘        (debate)    Manager        └─ Conservative ┘   Manager
```

**Every run costs real money, and more than people expect.** I verified the built graph:
20 nodes, of which **12 are LLM agents**. Twelve agents is the *floor* — analysts run
tool-calling loops that multiply their calls, and each extra debate round adds two more
agent turns (plus three per risk round). One ticker is a dozen-to-many-dozen LLM calls
against a frontier model. Read the cost section before running it on a watchlist.

## Setup

```bash
python .claude/skills/tradingagents/scripts/setup_tradingagents.py
```

Clones to `~/TradingAgents`, creates a venv at `~/.tradingagents-venv`, installs the
package (Python 3.10+). You then need one LLM provider key:

```bash
export OPENAI_API_KEY=...        # or ANTHROPIC_API_KEY / GOOGLE_API_KEY, matching llm_provider
export FRED_API_KEY=...          # optional — only for macro_data
```

Price and fundamentals default to **yfinance, which needs no key**, so an LLM key alone is
enough to run. Prediction markets default to Polymarket, also keyless.

## Check before you spend

```bash
python .claude/skills/tradingagents/scripts/preflight.py
```

It builds the agent graph **without making a single LLM call** (verified — construction is
offline), then reports the provider and models in force, which keys are present or missing,
the data vendors selected, and the floor on agent invocations for your current settings.
Run it after any config change and before any batch. It costs nothing.

## Running one analysis

```python
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

config = DEFAULT_CONFIG.copy()
config["max_debate_rounds"] = 1
config["quick_think_llm"] = "gpt-5.6-luna"   # cheap model for analysts
config["deep_think_llm"]  = "gpt-5.6"        # strong model for managers

ta = TradingAgentsGraph(selected_analysts=["market", "news"], debug=True, config=config)
_, decision = ta.propagate("NVDA", "2024-05-10")
print(decision)
```

`propagate(ticker, date)` returns `(final_state, decision)`. There is also an interactive
CLI — `tradingagents` — installed by the package.

Note `trade_date` is a **historical** date: the agents fetch data as of that day. That makes
runs reproducible-ish and lets you sanity-check a decision against what actually happened
next — the closest thing to evaluation this framework gives you for free.

## Controlling cost

In descending order of effect:

| Lever | Effect |
| --- | --- |
| `selected_analysts` | Drop from 4 to 1–2. Each analyst is an agent **plus** its tool loop — the biggest single saving. |
| `quick_think_llm` | Analysts and debaters use this. Point it at a cheap model; it does most of the calls. |
| `max_debate_rounds` | Each round adds a bull turn and a bear turn. Default 1. |
| `max_risk_discuss_rounds` | Each round adds three agent turns. Default 1. |
| `max_tokens` | Caps output per call — also the fix for a model that emits unbounded reasoning and hangs. |
| `deep_think_llm` | Only the managers use it, so a strong model here is comparatively cheap. |

Every key above is also settable as `TRADINGAGENTS_*` environment variables
(`TRADINGAGENTS_MAX_DEBATE_ROUNDS`, `TRADINGAGENTS_QUICK_THINK_LLM`, …), so you can tune a
run without editing code. Invalid values raise at startup rather than silently defaulting.

Set `checkpoint_enabled: True` before long or batch runs — LangGraph then saves state per
node, so a crash resumes instead of re-paying for the whole pipeline.

## Reading the output honestly

The decision arrives with confident prose and a clear verdict, which is exactly what makes
it easy to over-trust. What it actually is: a set of LLMs reasoning over recent data and
arguing. That is not a backtested edge, and the framework ships no evidence that its
decisions beat holding the index. Treat a run as structured research that surfaces
considerations you might have missed — bull and bear cases, risk framings — not as a signal.

The authors state plainly that this is for research. Two specific cautions worth carrying:
the same ticker and date can produce different decisions across runs (LLM sampling; setting
`temperature` reduces but does not eliminate it), and the agents can only see what their
data vendors return, so a decision made on a thin news day rests on thin evidence without
saying so.

`references/configuration.md` covers providers, vendors and every config key.
`references/agents.md` covers what each of the twelve agents does and how they interact.
