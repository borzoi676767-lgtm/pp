# Ollama API reference

Contents: [Endpoints](#endpoints) · [Generate](#generate) · [Chat](#chat) · [Options](#options) · [Structured outputs](#structured-outputs) · [Tool calling](#tool-calling) · [Embeddings](#embeddings) · [Model management](#model-management) · [OpenAI compatibility](#openai-compatibility) · [Clients](#client-libraries)

Base URL `http://localhost:11434`. No authentication.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/generate` | Single-prompt completion |
| POST | `/api/chat` | Multi-turn chat, tools, images |
| POST | `/api/embed` | Embeddings (batch) |
| POST | `/api/create` | Build a model from a Modelfile |
| POST | `/api/pull` / `/api/push` | Fetch or publish a model |
| POST | `/api/show` | Model metadata, template, parameters, capabilities |
| POST | `/api/copy` | Duplicate a model |
| DELETE | `/api/delete` | Remove a model |
| GET | `/api/tags` | Installed models |
| GET | `/api/ps` | Currently loaded models |
| GET | `/api/version` | Server version |

## Generate

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3", "prompt": "Why is the sky blue?", "stream": false,
  "system": "Answer in one sentence.",
  "options": {"temperature": 0.7, "num_ctx": 16384}
}'
```

Responses stream newline-delimited JSON by default; `"stream": false` returns one object.
Fields worth reading on every response:

- `prompt_eval_count` — tokens of your prompt the model actually read. Compare it against
  what you sent; a smaller number means silent truncation, not an error.
- `eval_count` / `eval_duration` (ns) — `eval_count / (eval_duration / 1e9)` is tokens/sec.
- `done_reason` — `stop`, `length` (hit `num_predict`), or `load`.
- `context` — an opaque token array you can pass back to continue statelessly.

`"think": false` suppresses the reasoning block on thinking models (qwen3, deepseek-r1).
`"raw": true` skips template application when you are supplying a fully-formatted prompt.
`"keep_alive": "30m"` or `-1` controls how long the model stays resident (default 5m).

## Chat

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3", "stream": false,
  "messages": [
    {"role": "system", "content": "You are terse."},
    {"role": "user", "content": "Capital of France?"}
  ]
}'
```

Roles: `system`, `user`, `assistant`, `tool`. Vision models take `"images"` on a message as
an array of base64-encoded strings. Chat is stateless — resend the full message list each
turn, which means a long conversation eventually collides with the context limit and gets
truncated from the front, dropping the system prompt first.

## Options

Passed in `"options"`, or set in a Modelfile with `PARAMETER`:

| Option | Meaning |
| --- | --- |
| `num_ctx` | Context window. The single most consequential setting; usable prompt is about half of it. |
| `num_predict` | Max tokens to generate (`-1` unlimited). |
| `temperature`, `top_k`, `top_p`, `min_p` | Sampling. |
| `repeat_penalty`, `repeat_last_n` | Repetition control. |
| `seed` | Fixed seed for reproducible output (pair with `temperature: 0`). |
| `stop` | Array of stop strings. |
| `num_gpu` | Layers offloaded to GPU; `0` forces CPU. |
| `num_thread` | CPU threads. |

## Structured outputs

Pass a JSON Schema as `format` and the response is constrained to it. Verified working:

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3", "stream": false, "think": false,
  "format": {"type":"object",
             "properties":{"city":{"type":"string"},"population":{"type":"integer"}},
             "required":["city","population"]},
  "messages":[{"role":"user","content":"Paris has about 2.1 million people. Extract city and population."}]
}'
# -> {"city": "Paris", "population": 2100000}
```

`"format": "json"` is the looser older form: valid JSON, no schema. The content still comes
back as a *string* that you parse — the schema constrains generation, it does not change the
envelope. Instructing the model in the prompt to produce JSON as well improves reliability.

## Tool calling

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3", "stream": false, "think": false,
  "tools": [{"type":"function","function":{
      "name":"get_weather","description":"Get weather for a city",
      "parameters":{"type":"object","properties":{"city":{"type":"string"}},
                    "required":["city"]}}}],
  "messages":[{"role":"user","content":"What is the weather in Tokyo?"}]
}'
# -> message.tool_calls: [{"function": {"name": "get_weather", "arguments": {"city": "Tokyo"}}}]
```

`arguments` arrives as a parsed object, not a JSON string as in the OpenAI API. Append the
result as a `{"role": "tool", "content": "..."}` message and call again. Only models whose
`/api/show` capabilities include `tools` will emit tool calls; others silently answer in
prose instead of erroring.

## Embeddings

```bash
curl http://localhost:11434/api/embed -d '{"model":"nomic-embed-text","input":["hello","world"]}'
```

`input` takes a string or an array. Generation models cannot embed — asking a chat model
returns `"This server does not support embeddings"`. Use a purpose-built model
(`nomic-embed-text`, `mxbai-embed-large`, `all-minilm`). Embeddings from different models
are not comparable, so re-embed the whole corpus if you switch.

## Model management

```bash
curl http://localhost:11434/api/pull -d '{"model":"qwen3:8b"}'     # streams progress
curl http://localhost:11434/api/show -d '{"model":"qwen3"}'        # template, params, caps
curl http://localhost:11434/api/tags                               # installed
curl http://localhost:11434/api/ps                                 # loaded right now
curl -X DELETE http://localhost:11434/api/delete -d '{"model":"old-model"}'
```

`/api/show` is the authoritative source for a model's real context limit — look for the
family-prefixed key in `model_info`, e.g. `qwen3.context_length`. `/api/ps` reports
`context_length` as actually loaded, which is the number that governs truncation.

Note `size_vram` in `/api/ps` is not a dependable GPU indicator: on a CPU-only machine it
still reported 414 MB. To confirm placement, read the `ollama serve` startup log for
`inference compute ... library=cpu|cuda|rocm` and `total_vram`.

## OpenAI compatibility

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")  # any non-empty key
client.chat.completions.create(model="qwen3", messages=[{"role":"user","content":"hi"}])
```

Supports `/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`, `/v1/models`. Good for
pointing existing tooling at a local model with a one-line change.

Two limits worth knowing. There is no `think` field, so on a thinking model the reasoning
block consumes your `max_tokens` budget — `max_tokens: 20` against qwen3 returned an empty
`content` with all 20 tokens spent on reasoning, while 300 returned normal text plus a
`reasoning` field. And `num_ctx` cannot be set here at all, so the context fix has to come
from `OLLAMA_CONTEXT_LENGTH` or a Modelfile.

## Client libraries

```bash
pip install ollama        # ollama.chat(model=..., messages=[...])
npm install ollama        # import ollama from 'ollama'
```

Both wrap the REST API, default to `http://localhost:11434`, and expose streaming as an
iterator. Anything the libraries do can be done with `curl`; they mainly save you the
streaming plumbing.
