# The agents and how they interact

Verified by building the graph: **20 nodes, 12 of them LLM agents.** The other 8 are
plumbing — four `tools_*` nodes (the analysts' tool-calling loops) and four `Msg Clear`
nodes that trim message history between stages.

## Flow

```
1. ANALYSTS (parallel, each with a tool loop)
   Market Analyst        price action, technical indicators
   Sentiment Analyst     multi-source sentiment for the ticker
   News Analyst          ticker + macro headlines, summarized into a table
   Fundamentals Analyst  financial statements, valuation
        ↓ reports
2. RESEARCH DEBATE            (max_debate_rounds — 2 agent turns per round)
   Bull Researcher ⇄ Bear Researcher
        ↓
   Research Manager           adjudicates, produces an investment plan
        ↓
3. Trader                     turns the plan into a concrete proposal
        ↓
4. RISK DEBATE                (max_risk_discuss_rounds — 3 agent turns per round)
   Aggressive · Neutral · Conservative analysts argue the risk
        ↓
5. Portfolio Manager          final BUY / SELL / HOLD
```

## Choosing analysts

```python
TradingAgentsGraph(selected_analysts=["market", "news"], config=config)
```

Valid: `market`, `social`, `news`, `fundamentals` (all four by default). This is the single
biggest cost lever — each analyst is an agent **plus** an unbounded tool loop, so dropping
from four to two removes far more than two calls. `social_media_analyst` is a
backwards-compatibility shim for the renamed sentiment analyst.

## Why the debate structure matters

The bull/bear and aggressive/neutral/conservative pairings exist to force the model to
argue against itself rather than confirm its first read. That is a real benefit over a
single prompt — you get an explicit counter-case.

It is not a correctness guarantee. Both sides are the same model reasoning over the same
retrieved evidence, so shared blind spots stay shared: if the news vendor returned nothing
useful, both the bull and the bear argue from the same thin base and the disagreement looks
substantive while resting on very little. Read the analyst reports, not just the verdict.

More debate rounds produce more thorough argument, not more accurate ones. Raise
`max_debate_rounds` when you want the reasoning surfaced for your own reading; do not treat
a 3-round decision as more reliable than a 1-round one.

## Output

`propagate(ticker, date)` returns `(final_state, decision)`. `final_state` carries each
agent's report — usually more useful than the verdict, since it shows what was considered.
Reports and logs land under `~/.tradingagents/logs/`.

`trade_date` is historical: agents fetch data as of that day. That gives you a cheap
evaluation loop — run a past date, then compare the decision against what the price actually
did. Do that before trusting the framework on a live date.
