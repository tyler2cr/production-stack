# Reproducing the kvaware chat-tokenization before/after

Any machine with 2 CUDA GPUs — or 1 GPU: add `GPU1=0 GPU_MEM=0.4` to every
command's environment to put both engines on device 0. Model is small and
ungated; total setup is minutes. `ROUTER_REF` must be exported for EVERY
`docker compose` invocation (the compose file interpolates it, including for
`rm`).

```bash
export HOST_IP=$(hostname -I | awk '{print $1}')   # workers register with this IP;
                                                   # loopback backends 500 on kv-followed requests
# BEFORE — upstream merge-base (unpatched):
export ROUTER_REF=58a0935955d5b29f615c784a3533ff2433075bdd
docker compose build && docker compose up -d
# wait for both engines:
#   curl -s localhost:8100/v1/models && curl -s localhost:8200/v1/models
# and for BOTH workers to register with the controller:
#   docker logs router 2>&1 | grep -c "Registered instance"   # want: 2
python3 -m venv .venv && .venv/bin/pip install httpx   # bare pip/ensurepip may be absent (PEP 668 / minimal images)
.venv/bin/python probe.py
# expect: chat requests ALTERNATE engines (same prefix prefilled on both),
#         no "found by kvaware router" lines for chat in `docker logs router`;
#         prompt-form pair DOES kv-follow.

# AFTER — the PR head (immutable sha; equals branch router-kvaware-chat-completions).
# The hardware e2e in the results doc ran at 3f498ff; the commits after it
# are review-hardening only (executors for blocking I/O, graceful fallback
# on tokenize failure, single-flight tokenizer init, normalization tidying,
# shared _ensure_tokenizer helper, negative-cached failed loads).
export ROUTER_REF=d34db2c
docker compose rm -sf router
docker compose build router && docker compose up -d router
# the recreated router's worker registry starts EMPTY - wait for both
# workers to re-register (heartbeat interval 10s):
#   docker logs router 2>&1 | grep -c "Registered instance"   # want: 2
.venv/bin/python probe.py   # fresh salt is generated per run
# expect: chat reqs 2-4 pin to the engine that served req 1 (wall_s drops),
#         "found by kvaware router" in `docker logs router`;
#         prompt-form behavior unchanged.
```

Wiring notes (each was a silent failure when wrong - see the compose/Dockerfile
comments): identical image base for router and engines (vLLM-rooted NONE_HASH),
matched lmcache versions (version-locked ZMQ messages), `PYTHONHASHSEED=0` on
both sides, `LMCACHE_LMCACHE_WORKER_HEARTBEAT_TIME` set (0.4.x default never
heartbeats; the controller reaps at 30s), host networking (the controller
advertises `get_ip()`), and distinct worker ports per engine on one host.
