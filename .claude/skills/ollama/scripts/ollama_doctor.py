#!/usr/bin/env python3
"""Diagnose a local Ollama setup.

Checks the three things that silently degrade local inference:

  1. Context window   - Ollama sizes the window from available VRAM, not from what
                        the model supports, and truncates over-long prompts without
                        an error. This is the most common cause of a "dumb" model.
  2. Placement        - weights on CPU instead of GPU, which costs an order of
                        magnitude in speed.
  3. Throughput       - measured tokens/sec, so "slow" becomes a number.

Standard library only; no pip install required.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")


def base_url(host):
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host.rstrip("/")


def call(url, path, payload=None, timeout=600):
    req = urllib.request.Request(
        url + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def human(n):
    if not isinstance(n, (int, float)) or n <= 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def model_max_context(show):
    """The model's real context limit, under a family-prefixed key."""
    for k, v in (show.get("model_info") or {}).items():
        if k.endswith(".context_length") and isinstance(v, int):
            return v
    return None


def runtime_entry(url, model):
    for m in (call(url, "/api/ps").get("models") or []):
        if m.get("name") == model or m.get("model") == model:
            return m
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default=DEFAULT_HOST, help=f"default: {DEFAULT_HOST}")
    ap.add_argument("--model", default=None,
                    help="model to inspect (default: first loaded, else first installed)")
    ap.add_argument("--no-truncation-test", action="store_true",
                    help="skip the prompt-budget probe (it costs one prompt eval)")
    ap.add_argument("--target-prompt-tokens", type=int, default=8000,
                    help="longest prompt you intend to send (default: 8000). The context "
                         "check is judged against this, not against the model's maximum.")
    ap.add_argument("--num-ctx", type=int, default=None,
                    help="load the model with this context size instead of the default")
    args = ap.parse_args()
    url = base_url(args.host)

    print(f"Ollama doctor — {url}\n" + "=" * 66)

    try:
        version = call(url, "/api/version", timeout=10).get("version", "?")
    except (urllib.error.URLError, OSError) as exc:
        print(f"Cannot reach the Ollama server at {url}: {exc}")
        print("Start it with 'ollama serve', or set --host / OLLAMA_HOST.")
        return 2
    print(f"server version   {version}")

    tags = (call(url, "/api/tags").get("models") or [])
    print(f"installed models {len(tags)}")
    for m in sorted(tags, key=lambda m: -m.get("size", 0))[:10]:
        d = m.get("details") or {}
        print(f"  {m['name']:<34} {human(m.get('size')):>9}  "
              f"{d.get('parameter_size', '?')} {d.get('quantization_level', '')}")
    if len(tags) > 10:
        print(f"  ... and {len(tags) - 10} more")
    if not tags:
        print("\nNo models installed. Try: ollama pull qwen3:0.6b")
        return 2

    model = args.model
    if not model:
        loaded = call(url, "/api/ps").get("models") or []
        model = loaded[0]["name"] if loaded else tags[0]["name"]
        print(f"\n(no --model given, inspecting {model})")

    try:
        show = call(url, "/api/show", {"model": model})
    except urllib.error.HTTPError:
        print(f"\nModel {model!r} is not installed. Pull it first: ollama pull {model}")
        return 2

    print(f"\nModel: {model}")
    det = show.get("details") or {}
    caps = show.get("capabilities") or []
    print(f"  parameters       {det.get('parameter_size', '?')}")
    print(f"  quantization     {det.get('quantization_level', '?')}")
    print(f"  capabilities     {', '.join(caps) if caps else '(none reported)'}")
    max_ctx = model_max_context(show)
    print(f"  max context      {max_ctx if max_ctx else 'unknown'}")

    # Load the model (and measure how long that takes) with a trivial generation.
    opts = {"num_predict": 1}
    if args.num_ctx:
        opts["num_ctx"] = args.num_ctx
    t0 = time.time()
    call(url, "/api/generate",
         {"model": model, "prompt": "hi", "stream": False, "think": False, "options": opts})
    load_s = time.time() - t0

    rt = runtime_entry(url, model)
    run_ctx = rt.get("context_length") if rt else None
    print(f"\nRuntime")
    print(f"  load time        {load_s:.1f}s")
    if rt:
        print(f"  resident size    {human(rt.get('size'))}")
        print(f"  size_vram        {human(rt.get('size_vram'))}   "
              f"(not a reliable GPU indicator — see notes)")
    print(f"  context in use   {run_ctx if run_ctx else 'unknown'}")

    problems = []
    # The usable prompt budget is about HALF of num_ctx: measured at 0.500-0.501
    # across num_ctx of 2048/4096/8192/16384 on ollama 0.33.3. The rest of the
    # window is held back for generation. So sizing num_ctx to your prompt length
    # is off by 2x, which is why this compares against run_ctx/2.
    est_budget = run_ctx // 2 if run_ctx else None
    if run_ctx:
        print(f"  usable prompt    ~{est_budget} tokens (about half the window)")
    if max_ctx and run_ctx and run_ctx < max_ctx:
        print(f"  headroom         {run_ctx} of the model's {max_ctx}")
    if est_budget and est_budget < args.target_prompt_tokens:
        print(f"\n  ** Prompts over ~{est_budget} tokens are truncated from the FRONT, with **")
        print(f"  ** no error, and you said you want to send {args.target_prompt_tokens}. **")
        print("  Instructions at the top of a prompt are the first thing discarded, so the")
        print("  model answers from a partial input rather than failing loudly.")
        problems.append("context")

    # Throughput.
    t0 = time.time()
    gen = call(url, "/api/generate", {
        "model": model, "stream": False, "think": False,
        "prompt": "Write a single paragraph about the sea.",
        "options": dict(opts, num_predict=120)})
    wall = time.time() - t0
    ec, ed = gen.get("eval_count"), gen.get("eval_duration")
    if ec and ed:
        tps = ec / (ed / 1e9)
        print(f"\nThroughput")
        print(f"  generation       {tps:.1f} tok/s   ({ec} tokens, {wall:.1f}s wall)")
        if tps < 15:
            print("  Slow enough to suggest CPU inference or an oversized model. Check the")
            print("  'ollama serve' startup log for: inference compute ... library=")
            problems.append("throughput")

    # Truncation probe: send more than the window and see how much was read.
    if not args.no_truncation_test and run_ctx:
        # Deliberately overflow the window and see how much survives. This measures
        # the real budget rather than proving truncation, which overflowing always
        # would.
        want = int(run_ctx * 1.5)
        filler = " ".join(f"word{i}" for i in range(want))
        probe = call(url, "/api/generate", {
            "model": model, "prompt": filler, "stream": False, "think": False,
            "options": dict(opts, num_predict=1)})
        read = probe.get("prompt_eval_count")
        print(f"\nMeasured prompt budget")
        print(f"  overflowed the window on purpose; the model read {read} tokens")
        if read:
            print(f"  -> anything past ~{read} tokens is dropped, silently, from the front")
            if read < args.target_prompt_tokens and "context" not in problems:
                problems.append("context")

    print("\n" + "=" * 66)
    if "context" in problems:
        # Budget is ~half the window, so ask for twice the prompt you want to send.
        want = args.target_prompt_tokens * 2
        if max_ctx:
            want = min(want, max_ctx)
        print(f"Raise the context window. You want ~{args.target_prompt_tokens} prompt tokens,")
        print(f"and the usable budget is half the window, so ask for {want}:\n")
        print(f'  per request:  "options": {{"num_ctx": {want}}}')
        print(f"  per server:   OLLAMA_CONTEXT_LENGTH={want} ollama serve")
        print(f"  baked in:     printf 'FROM {model}\\nPARAMETER num_ctx {want}\\n' > Modelfile")
        print(f"                ollama create {model.split(':')[0]}-ctx -f Modelfile")
        print("\nThe KV cache grows with the window, so this costs memory — raising it on a")
        print("machine that was already tight pushes layers onto the CPU. Re-run to see.")
    if "throughput" in problems:
        print("\nFor speed: use a smaller model or a heavier quantization (Q4_K_M is the")
        print("usual sweet spot), and confirm the GPU is actually being used.")
    if not problems:
        print("No context truncation or obvious performance problem detected.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
