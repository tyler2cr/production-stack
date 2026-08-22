# One image for engines AND router: identical vllm+lmcache+hash chain on both
# sides (see compose comments). lmcache version must match on controller
# (router) and workers (engines) - the ZMQ messages are version-locked.
FROM vllm/vllm-openai:v0.22.0 AS base
RUN pip install --no-cache-dir lmcache==0.4.5

FROM base AS router
RUN apt-get update && apt-get install -y -q git && rm -rf /var/lib/apt/lists/*
ARG ROUTER_REF
RUN pip install --no-cache-dir "vllm-router @ git+https://github.com/tyler2cr/production-stack.git@${ROUTER_REF}"
ENTRYPOINT ["vllm-router"]
