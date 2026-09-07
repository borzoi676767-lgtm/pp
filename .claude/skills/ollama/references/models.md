# Choosing, customizing and tuning models

Contents: [Sizing](#sizing-a-model-to-the-machine) · [Quantization](#quantization) · [Picking](#picking-a-model) · [Modelfile](#modelfile) · [Environment](#server-environment-variables) · [Performance](#performance) · [Storage](#storage)

## Sizing a model to the machine

The weights must fit in VRAM, or Ollama splits them across GPU and CPU and generation slows
by roughly an order of magnitude. A workable estimate for a Q4 quantization:

| Parameters | Weights at Q4 | Comfortable VRAM/RAM |
| --- | --- | --- |
| 1B | ~0.7 GB | 2 GB |
| 3B | ~2 GB | 4 GB |
| 7-8B | ~4.5 GB | 8 GB |
| 13-14B | ~8 GB | 12 GB |
| 32-34B | ~19 GB | 24 GB |
| 70B | ~40 GB | 48 GB |

Add the KV cache on top, and it grows with `num_ctx`. This is not a rounding error: on the
test machine, raising `num_ctx` from 4096 to 16000 took a 0.6B model's resident footprint
from 977 MB to 2.3 GB. Budget context alongside weights, not after them.

With no GPU, models still run on CPU — a 0.6B model managed ~56 tok/s on 4 cores, which is
usable; a 7B model on the same hardware would be a few tok/s, which is not.

## Quantization

Tags encode it: `qwen3:8b-q4_K_M`. Lower bits mean smaller and faster with more quality loss.

- **Q4_K_M** — the default and the usual right answer. Roughly 4 bits, minor quality cost.
- **Q5_K_M / Q6_K** — closer to full quality, noticeably larger.
- **Q8_0** — near-lossless, about 2× Q4.
- **fp16** — unquantized, 4× Q4. Rarely worth it for local inference.
- **Q3 / Q2** — visible degradation. Prefer a smaller model at Q4 over a larger one at Q2.

A 14B at Q4 generally beats an 8B at Q8 for the same memory, so spend memory on parameters
before precision — until you hit Q3, where it stops being true.

## Picking a model

`ollama.com/library` is the catalogue. Reasonable starting points:

| Need | Try |
| --- | --- |
| General chat / instruction following | `qwen3`, `llama3.2`, `gemma3` |
| Code | `qwen2.5-coder`, `deepseek-coder-v2`, `codellama` |
| Reasoning | `deepseek-r1`, `qwen3` (thinking mode) |
| Embeddings | `nomic-embed-text`, `mxbai-embed-large` |
| Vision | `llava`, `llama3.2-vision`, `qwen2.5vl` |
| Tiny / smoke tests | `qwen3:0.6b`, `llama3.2:1b` |

Check `/api/show` capabilities before designing around a feature — `tools`, `thinking`,
`vision`, `completion`, `embedding` are reported per model, and a model without `tools`
answers in prose instead of emitting tool calls.

## Modelfile

The durable way to fix settings so callers can't forget them:

```
FROM qwen3:8b
PARAMETER num_ctx 16384
PARAMETER temperature 0.3
PARAMETER stop "<|im_end|>"
SYSTEM "You are a concise code reviewer. Point out bugs, not style."
```

```bash
ollama create reviewer -f Modelfile
ollama run reviewer "review this function..."
```

Instructions: `FROM` (base model or a GGUF path), `PARAMETER`, `SYSTEM`, `TEMPLATE` (the
prompt format — rarely worth overriding), `ADAPTER` (a LoRA), `LICENSE`, `MESSAGE`
(few-shot priming turns).

Verified: a Modelfile with `PARAMETER num_ctx 8192` produced a model that `/api/ps` reported
running at 8192 rather than the VRAM-derived default. This is the fix that survives server
restarts and callers who don't pass `options`.

`ollama show <model> --modelfile` prints the effective Modelfile of any model, which is the
easiest way to see the template and defaults it was built with.

## Server environment variables

| Variable | Effect |
| --- | --- |
| `OLLAMA_CONTEXT_LENGTH` | Default context for every model. The global fix for truncation. |
| `OLLAMA_HOST` | Bind address (default `127.0.0.1:11434`). |
| `OLLAMA_MODELS` | Where weights are stored — point it at a big disk. |
| `OLLAMA_KEEP_ALIVE` | How long models stay resident (default `5m`; `-1` pins). |
| `OLLAMA_MAX_LOADED_MODELS` | Models resident at once. |
| `OLLAMA_NUM_PARALLEL` | Concurrent requests per model (default 1). Memory scales as `NUM_PARALLEL x CONTEXT_LENGTH`. |
| `OLLAMA_FLASH_ATTENTION` | Enables flash attention where supported. |
| `OLLAMA_KV_CACHE_TYPE` | `q8_0` / `q4_0` quantize the KV cache, buying context at some quality cost. |
| `OLLAMA_MAX_QUEUE` | Queue depth before requests are rejected. |

`OLLAMA_NUM_PARALLEL` interacts with context multiplicatively: each concurrent slot gets its
own window, so required memory scales as `OLLAMA_NUM_PARALLEL * OLLAMA_CONTEXT_LENGTH`.
Raising both at once is the fast route to pushing a model onto the CPU.

## Performance

- Confirm GPU use from the `ollama serve` startup log (`inference compute ... library=`),
  not from `size_vram` in `/api/ps`, which reports non-zero even on CPU-only machines.
- Measure rather than guess: `eval_count / (eval_duration / 1e9)` from any response, or run
  `scripts/ollama_doctor.py`.
- First request after idle is slow because the model is loading. Raise `keep_alive` for an
  interactive workload; leave it low if you are rotating between models on a small machine.
- If a model is too slow: smaller model, then heavier quantization, then shorter context —
  in that order, since each is a smaller quality sacrifice than the last.
- `num_gpu` sets how many layers go to the GPU. Lowering it deliberately can help when the
  automatic split is thrashing; `0` forces CPU.

## Storage

Models live in `~/.ollama/models` (`OLLAMA_MODELS` to relocate) and are stored as
content-addressed blobs, so tags sharing layers share disk. `ollama list` shows sizes,
`ollama rm` deletes. Pulling a few 7B models will consume tens of gigabytes; check free
space before a bulk pull rather than after.
