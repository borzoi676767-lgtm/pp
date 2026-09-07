---
name: ollama
description: Run open-weight LLMs locally with Ollama (github.com/ollama/ollama) — install it, pick a model that fits the machine, and call it from code. Use this whenever the user mentions ollama, running an LLM locally/offline/on-prem, `ollama run` or `ollama pull`, a local model server on port 11434, llama/qwen/gemma/mistral/deepseek weights on their own hardware, private inference without sending data to an API, or asks why their local model is slow, truncating input, ignoring its system prompt, or returning empty responses. Covers the REST API, the OpenAI-compatible endpoint, structured outputs, tool calling, embeddings, and Modelfile customization.
---

# Ollama

Ollama runs open-weight models locally: a background server on port 11434, a CLI, and a REST
API. `ollama run qwen3` pulls the weights and gives you a chat prompt; everything else is
detail on top of that.

The detail that matters most, because it fails silently: **Ollama picks a context window
based on available VRAM, not on what the model supports, and quietly drops the front of any
prompt that doesn't fit.** No error, no warning — just an answer based on part of your input.
The `doctor` script below exists mainly to catch that.

## Setup

```bash
bash .claude/skills/ollama/scripts/setup_ollama.sh
```

Downloads the official installer, shows you what it will do, installs, and starts the server.
`--no-systemd` installs the binary and runs `ollama serve` directly, for containers and
machines without systemd. On macOS use the app from ollama.com; on Windows, the installer.

Verify and pull a small model to prove the loop works:

```bash
ollama pull qwen3:0.6b && ollama run qwen3:0.6b "say hello"
```

## Check the setup before trusting output

```bash
python .claude/skills/ollama/scripts/ollama_doctor.py --model qwen3:0.6b
```

It reports the server version, every installed model, and for the target model: the context
window actually in force versus the model's real maximum, measured generation throughput,
and whether the weights landed in VRAM or are running on CPU. Run it whenever a local model
behaves oddly — most "the model is dumb" reports are one of those three.

## The context trap

Measured on a CPU-only box with `qwen3:0.6b` (a model advertising 40,960 tokens):

```
ollama serve log:  "vram-based default context" total_vram="0 B" default_num_ctx=4096
/api/ps:           context_length: 4096          ← not 40960
```

Sending an ~8,200-token prompt to that server: `prompt_eval_count` came back as **2050**.
Ollama kept the *end* of the prompt and discarded everything before it. With the key fact
placed at the start, the model confidently made an answer up rather than erroring.

**The usable prompt is half the window, not all of it.** Overflowing the context at four
different sizes gave a consistent ratio of 0.500 — the rest is reserved for generation:

| `num_ctx` | tokens actually read |
| --- | --- |
| 2048 | 1026 |
| 4096 | 2050 |
| 8192 | 4098 |
| 16384 | 8194 |

So to fit an N-token prompt, ask for `num_ctx` of about **2N**. Sizing the window to your
prompt length leaves you truncating at half of it. A long document followed by a question
survives by luck — the question is at the end, and it's the document that gets cut — while
instructions at the top are the first thing lost.

Three ways to set it, in increasing order of durability:

```bash
# per request
curl http://localhost:11434/api/generate -d '{"model":"qwen3","prompt":"...",
  "options":{"num_ctx":16384}}'

# per server, for every model
OLLAMA_CONTEXT_LENGTH=16384 ollama serve

# baked into a model, survives restarts and callers that forget
printf 'FROM qwen3\nPARAMETER num_ctx 16384\n' > Modelfile
ollama create qwen3-16k -f Modelfile
```

Context costs memory — the KV cache grows with `num_ctx`, so raising it on a machine that
was already tight pushes layers onto the CPU and slows generation. Going from 4096 to 16000
on the test box took the resident model from 977 MB to 2.3 GB for the same 0.6B weights.
Raise it to twice the prompt you actually send, not to the model's maximum, and re-run the
doctor to confirm what you got.

## Calling it

```bash
curl http://localhost:11434/api/generate -d '{"model":"qwen3","prompt":"Why is the sky blue?","stream":false}'
curl http://localhost:11434/api/chat -d '{"model":"qwen3","messages":[{"role":"user","content":"hi"}],"stream":false}'
```

Responses stream by default — set `"stream": false` for a single JSON object. Useful response
fields: `eval_count` / `eval_duration` (throughput), `prompt_eval_count` (**how much of your
prompt actually got read** — compare it against what you sent), and `done_reason`.

The OpenAI-compatible endpoint at `/v1/chat/completions` lets existing SDKs point at Ollama
by changing `base_url` to `http://localhost:11434/v1` and passing any non-empty API key.

`references/api.md` covers the full endpoint list, streaming, structured outputs (verified
working with a JSON schema), tool calling, embeddings, and the Python/JS clients.
`references/models.md` covers choosing a model for the hardware you have, quantization,
Modelfiles, and the environment variables that control the server.

## Things that look like model failures but aren't

- **Empty response from `/v1/chat/completions`.** Thinking models spend completion tokens on
  reasoning before any content. With `max_tokens: 20`, qwen3 returned `""` — the budget went
  entirely to the reasoning block. Raise `max_tokens`, or use `/api/chat` with
  `"think": false`, which the OpenAI endpoint has no field for.
- **"This server does not support embeddings."** Generation models can't embed. Pull a real
  embedding model (`nomic-embed-text`, `mxbai-embed-large`) and call `/api/embed`.
- **First request is slow, later ones fast.** Loading weights. Models unload after 5 minutes
  idle by default; `"keep_alive": "30m"` (or `-1` to pin) keeps them resident.
- **Generation is uniformly slow.** The model is on CPU. Check the `ollama serve` startup log
  for `inference compute ... library=` and `total_vram`. Note that `size_vram` in `/api/ps`
  is *not* a reliable GPU indicator — on a CPU-only box it still reported 434 MB.

## Exposing the server

Ollama binds to `127.0.0.1` and has no authentication. `OLLAMA_HOST=0.0.0.0` puts an
unauthenticated model server on the network, where anyone who can reach the port can run
inference, pull models, and delete them. If it needs to be reachable, put a reverse proxy
with auth in front of it rather than changing the bind address alone.
