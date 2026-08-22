# Reproducing the kvaware chat-tokenization before/after

Any machine with 2 CUDA GPUs (or 1 GPU: put both engines on device 0 and set
`GPU_MEM=0.4`). Model is small and ungated; total setup is minutes.

```bash
# BEFORE - upstream merge-base (unpatched):
ROUTER_REF=58a0935955d5b29f615c784a3533ff2433075bdd docker compose build && \
  ROUTER_REF=58a0935955d5b29f615c784a3533ff2433075bdd docker compose up -d
# wait for both engines: curl localhost:8100/v1/models && curl localhost:8200/v1/models
# and for both workers to register: docker logs router | grep "Registered instance"
pip install httpx && python3 probe.py
# expect: chat requests ALTERNATE engines (same prefix prefilled on both),
#         no "found by kvaware router" lines for chat in `docker logs router`;
#         prompt-form pair DOES kv-follow.

# AFTER - the PR branch (patched):
docker compose rm -sf router
ROUTER_REF=router-kvaware-chat-completions docker compose build router && \
  ROUTER_REF=router-kvaware-chat-completions docker compose up -d router
python3 probe.py   # fresh salt is generated per run
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
