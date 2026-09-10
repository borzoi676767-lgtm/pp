#!/usr/bin/env python3
"""Check a TradingAgents setup without spending anything.

Builds the agent graph — which happens entirely offline — then reports the
provider and models in force, which API keys are present, the data vendors
selected, and a floor on how many LLM agent invocations one propagate() will
cost at the current settings.

Makes no LLM calls. Safe to run as often as you like.
"""
import argparse
import importlib
import os
import sys

# The package owns the canonical provider -> key-env mapping, including the
# providers that legitimately need no key (bedrock uses the AWS credential
# chain; ollama is local). Import it rather than duplicating a guess — the
# provider names are not the ones you would guess (glm, not zhipu; qwen, not
# dashscope), and a stale local copy silently reports the wrong variable.
try:
    from tradingagents.llm_clients.api_key_env import (
        PROVIDER_API_KEY_ENV as PROVIDER_KEYS,
        get_api_key_env,
    )
    _CANONICAL = True
except ImportError:                                   # older checkout
    PROVIDER_KEYS = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
                     "google": "GOOGLE_API_KEY"}
    _CANONICAL = False

    def get_api_key_env(provider):
        return PROVIDER_KEYS.get(provider)
VENDOR_KEYS = {"fred": "FRED_API_KEY", "alpha_vantage": "ALPHA_VANTAGE_API_KEY"}
ALL_ANALYSTS = ("market", "social", "news", "fundamentals")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--analysts", nargs="+", default=None,
                    help=f"analysts to plan for (default: all — {' '.join(ALL_ANALYSTS)})")
    ap.add_argument("--tool-calls-per-analyst", type=int, default=3,
                    help="assumed tool-loop turns per analyst for the estimate (default 3)")
    ap.add_argument("--no-build", action="store_true",
                    help="skip graph construction (config report only)")
    args = ap.parse_args()

    try:
        cfg_mod = importlib.import_module("tradingagents.default_config")
    except ImportError:
        sys.exit("tradingagents is not importable. Run scripts/setup_tradingagents.py, "
                 "or activate the venv that has it installed.")
    config = cfg_mod.DEFAULT_CONFIG.copy()

    print("TradingAgents preflight\n" + "=" * 62)

    provider = config.get("llm_provider", "?")
    print("\nLLM")
    print(f"  provider          {provider}")
    print(f"  deep_think_llm    {config.get('deep_think_llm')}   (managers)")
    print(f"  quick_think_llm   {config.get('quick_think_llm')}   (analysts, debaters)")
    print(f"  backend_url       {config.get('backend_url') or '(provider default)'}")
    for opt in ("temperature", "max_tokens", "llm_max_retries"):
        print(f"  {opt:<17} {config.get(opt) if config.get(opt) is not None else '(provider default)'}")

    problems = []
    known = provider in PROVIDER_KEYS
    key = get_api_key_env(provider) if known else None
    print("\nCredentials"
          + ("" if _CANONICAL else "   (package mapping unavailable — using a minimal fallback)"))
    if key:
        present = bool(os.environ.get(key))
        print(f"  {key:<24} {'set' if present else '** MISSING **'}")
        if not present:
            problems.append(f"{key} is not set — every agent call will fail")
    elif known:
        # bedrock authenticates through the AWS chain; ollama is local.
        print(f"  {provider}: no API key env — authenticates another way (AWS chain, or local)")
    else:
        print(f"  unrecognized provider {provider!r} — check its key requirement manually")

    vendors = config.get("data_vendors", {})
    print("\nData vendors")
    for category, vendor in vendors.items():
        need = VENDOR_KEYS.get(str(vendor).split(",")[0].strip())
        if need:
            ok = bool(os.environ.get(need))
            print(f"  {category:<22} {vendor:<14} needs {need}: {'set' if ok else 'MISSING'}")
            if not ok:
                problems.append(f"{category} uses {vendor}, but {need} is not set")
        else:
            print(f"  {category:<22} {vendor:<14} (keyless)")

    analysts = tuple(args.analysts) if args.analysts else ALL_ANALYSTS
    debate = int(config.get("max_debate_rounds", 1))
    risk = int(config.get("max_risk_discuss_rounds", 1))

    print("\nRun shape")
    print(f"  analysts          {len(analysts)}  ({', '.join(analysts)})")
    print(f"  debate rounds     {debate}   -> {2 * debate} bull/bear turns")
    print(f"  risk rounds       {risk}   -> {3 * risk} risk-agent turns")
    print(f"  checkpointing     {config.get('checkpoint_enabled')}")

    # Floor: one turn per analyst, the debate turns, the risk turns, plus
    # research manager + trader + portfolio manager. Tool loops are extra and
    # unbounded, so the estimate is a lower bound, never a prediction.
    floor = len(analysts) + 2 * debate + 3 * risk + 3
    with_tools = len(analysts) * args.tool_calls_per_analyst + 2 * debate + 3 * risk + 3
    print("\nCost floor (LLM agent invocations per propagate)")
    print(f"  minimum           {floor}")
    print(f"  with ~{args.tool_calls_per_analyst} tool turns/analyst   ~{with_tools}")
    print("  Tool-calling loops are unbounded, so treat both as lower bounds. Multiply by")
    print("  your per-call cost, then by the number of tickers, before any batch run.")

    if not args.no_build:
        print("\nGraph construction (offline — no LLM calls)")
        if key:
            os.environ.setdefault(key, "preflight-placeholder")
        try:
            tg = importlib.import_module("tradingagents.graph.trading_graph")
            ta = tg.TradingAgentsGraph(debug=False, selected_analysts=list(analysts),
                                       config=config)
            nodes = list(getattr(ta.workflow, "nodes", []))
            print(f"  built OK — {len(nodes)} nodes")
            agents = [n for n in nodes
                      if not n.startswith("Msg Clear") and not n.startswith("tools_")]
            print(f"  {len(agents)} LLM agents: {', '.join(agents)}")
        except Exception as exc:                          # noqa: BLE001
            print(f"  BUILD FAILED: {type(exc).__name__}: {exc}")
            problems.append("graph construction failed — config or install problem")

    print("\n" + "=" * 62)
    if problems:
        print("Not ready:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("Config looks runnable. Nothing here validates decision quality — the framework")
    print("ships no evidence its output beats a benchmark. Treat runs as research.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
