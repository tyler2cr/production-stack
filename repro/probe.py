#!/usr/bin/env python3
"""KV-follow signature probe. Needs only httpx (pip install httpx).

Sends 4 chat requests sharing one long salted prefix through the router and
attributes each to an engine via vllm:prompt_tokens_total deltas, then a
2-request prompt-form pair.

PATCHED router: reqs 2-4 pin to the engine that served req 1 (KV-follow),
router logs "found by kvaware router". UNPATCHED: chat requests alternate
engines (QPS fallback), the shared prefix is prefilled on BOTH.
"""
import json, sys, time, uuid
import httpx

ROUTER = "http://127.0.0.1:30800"
ENGINES = {"engine0": "http://127.0.0.1:8100", "engine1": "http://127.0.0.1:8200"}
MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

def counters():
    out = {}
    for name, url in ENGINES.items():
        txt = httpx.get(url + "/metrics", timeout=5).text
        out[name] = sum(float(l.rsplit(" ", 1)[1]) for l in txt.splitlines()
                        if l.startswith("vllm:prompt_tokens_total"))
    return out

def delta(a, b):
    return {k: round(b[k] - a[k], 1) for k in a}

salt = uuid.uuid4().hex[:8]
# ~4k-token shared prefix (well above the router's 2k kv_aware_threshold)
history = [{"role": "user", "content": f"(salt {salt}) " + "the quick brown fox jumps over the lazy dog. " * 40},
           {"role": "assistant", "content": "Noted."}] * 12

print("== chat-completions (messages form) ==")
for i in range(4):
    body = {"model": MODEL, "max_tokens": 40,
            "messages": history + [{"role": "user", "content": f"Question {i+1}: summarize in one sentence."}]}
    before, t0 = counters(), time.monotonic()
    httpx.post(ROUTER + "/v1/chat/completions", json=body, timeout=120).raise_for_status()
    print(json.dumps({"req": i + 1, "wall_s": round(time.monotonic() - t0, 2),
                      "engine_prompt_token_delta": delta(before, counters())}))

print("== completions (prompt form, regression) ==")
prompt = f"(salt {salt}-p) " + "colorless green ideas sleep furiously. " * 400
for i in range(2):
    before, t0 = counters(), time.monotonic()
    httpx.post(ROUTER + "/v1/completions",
               json={"model": MODEL, "prompt": prompt, "max_tokens": 20}, timeout=120).raise_for_status()
    print(json.dumps({"prompt_req": i + 1, "wall_s": round(time.monotonic() - t0, 2),
                      "engine_prompt_token_delta": delta(before, counters())}))
