---
name: paper-desk
description: Run the six-agent PAPER trading desk (Scanner, Anti-FOMO, Sizer, Buyer, Prediction-Market and Logger subagents) on live keyless crypto/meme-coin and Polymarket/Kalshi data, with the fixed rules (1% max risk, one position, stop required, no chasing, no hidden losses, skip on disagreement) enforced by code in an append-only paper ledger. Use when the user wants to paper trade, run the desk or the 6-agent team on a token, scan meme coins for a paper setup, check or close paper positions, research a prediction market as a paper bet, or see paper-trading stats or the spreadsheet. Never places a real order.
---

# Paper desk: six agents, paper only

This skill makes the main conversation the desk's coordinator. It dispatches six subagents (`.claude/agents/paper-*.md`), each with one job. The rules don't depend on anyone's discipline: `scripts/desk.py` refuses any trade that breaks them and logs the refusal. `scripts/market.py` is the only source of prices.

`S` below means `.claude/skills/paper-desk/scripts`. Use `python` instead of `python3` on Windows.

## Never, while running the desk

- **Never call a broker or wallet order tool.** That covers Robinhood, Webull, or any `place_*`/`cancel_*` tool. No step of this skill sends a real order. If the user asks for a real trade mid-run, stop the desk and treat it as a separate request.
- **Never override a SKIP, BLOCK or REJECT.** Don't re-ask an agent until it agrees. Don't send a reworded setup to a fresh agent, and don't hand the Buyer a verdict an agent didn't give. When the agents disagree, the trade is skipped. One run, one decision.
- **Never do the math or quote a price yourself.** Agents run the scripts, and you relay what they return.

## Setup (once)

    python3 $S/desk.py status

If it says there's no ledger, create one with the user's paper balance (the guide's example is $1,000):

    python3 $S/desk.py init --balance 1000 [--pm-balance 1000] [--cost-bps 50] [--min-rr 1.5] [--max-stop-pct 25]

`--cost-bps` (assumed fee plus slippage per side) is the setting that matters most. On tight meme-coin stops it decides whether any setup clears the minimum reward/risk. Match it to the venue the user would really trade on. Settings are fixed once the first trade is logged, because changing rules mid-experiment is one of the guide's named mistakes.

## Run the desk on a token (guide step 8)

Read the desk's `cost_bps` from `desk.py status --json` and pass it to the Scanner.

1. **Scanner**: Agent `paper-scanner`, prompt: `Token: <name or symbol>. Desk cost per side: <cost_bps> bps.`
   - SKIP: `python3 $S/desk.py block --asset <SYMBOL> --stage scanner --reason "<its reason>" --setup "<its setup>"`, then step 5.
2. **Anti-FOMO**: Agent `paper-anti-fomo`, prompt: `Token: <SYMBOL>. Proposed entry: <a price from ENTRY AREA>.` Send nothing else. Its independence from the Scanner's pitch is the point.
   - BLOCK: `block --stage fomo --reason "<its explanation>"`, then step 5.
3. **Sizer**: Agent `paper-sizer`, prompt: `Size this crypto setup. Entry <E>, stop <S>, target <T>.`
   - REJECT: `block --stage sizer --reason "<its reasons>"`, then step 5.
4. **Buyer**: Agent `paper-buyer`, prompt with the three verdicts exactly as given (`Scanner = PASS`, `Anti-FOMO = APPROVE`, `Sizer = APPROVE`), plus the symbol, stop, target, the Scanner's SETUP and WHY as the reason, the planned entry, and Anti-FOMO's one-line explanation. It returns a ticket or TRADE BLOCKED, and either way the script has already logged it.
5. **Logger**: Agent `paper-logger`, prompt: the ids written this run (from `status`) and a one-line outcome. It adds a note if there's a lesson.

Then tell the user, compactly: each agent's verdict line, and the ticket or the reason it stopped. Skipping is a normal, successful result. Present it as the system working.

**Several tokens at once:** run the Scanners in parallel (one per token). Take the PASSes into step 2 in order of reward/risk after costs. Stop at the first one that gets a ticket, because the book holds one position. If a crypto position is already open, don't scan for new crypto entries: tell the user the desk is in a position.

## Check positions and exits

    python3 $S/desk.py check

This closes any position whose stop or target traded since entry. It walks the price bars, so a stop hit while nobody was looking still counts, and the fill rules are conservative (see references). Bets close when their market resolves. For each position it closes, run the Logger with the ids. When a book's closed count reaches a multiple of 20, the Logger also returns `stats`.

To keep it running: `/loop 15m /paper-desk check`.

Discretionary exit: `python3 $S/desk.py close --id <T-0001> --reason "<why>"` (fills at the live bid).

## Prediction-market idea (separate book)

1. Agent `paper-prediction-market`, prompt: `Market: <polymarket:slug | kalshi:TICKER | description to search>.`
   - SKIP: `block --book pm --asset <ref> --stage pm --reason "<why>"`, then step 4.
2. Agent `paper-sizer`, prompt: `Size this prediction-market bet: ref <ref>, side <YES|NO>, est-low <p>, est-high <p>, confidence <c>.` REJECT means `block --book pm --stage sizer`.
3. Agent `paper-buyer` with `Prediction-Market Agent = <YES|NO>` and `Sizer = APPROVE` verbatim, plus the ref, side, estimates, confidence, setup and reason.
4. Agent `paper-logger` with the ids.

## Reports and the spreadsheet

    python3 $S/desk.py stats            # wins, losses, win rate, avg win/loss, expectancy, drawdown, blocks, mistakes
    python3 $S/desk.py export           # paper-trading/trades.csv: summary on top, one row per trade/block
    python3 $S/desk.py verify           # proves no line was edited or removed

`trades.csv` opens directly in Google Sheets (File > Import) or Excel. Its first columns are the guide's, in the guide's order.

## Persisting

The ledger is `paper-trading/ledger.jsonl` in the project. In a cloud session, commit and push it after a run, or it's gone when the container is.

## Reference

- `references/rules.md`: each guide rule and the code that enforces it, every threshold, the paper-fill rules, and what this build adds to the guide.
- Tests: `python3 $S/test_desk.py` (offline).
