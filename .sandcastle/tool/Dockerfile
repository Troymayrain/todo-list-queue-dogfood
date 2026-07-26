FROM node:22-bookworm-slim

ARG AGENT_UID=1000
ARG AGENT_GID=1000

COPY --from=ghcr.io/astral-sh/uv:0.8.22 \
  /uv /uvx /usr/local/bin/

ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium

RUN apt-get update \
  && apt-get install --yes --no-install-recommends ca-certificates git python3 python3-venv \
    chromium \
    fonts-liberation \
  && rm -rf /var/lib/apt/lists/* \
  && npm install --global @anthropic-ai/claude-code@2.1.217 \
  && test -x /usr/bin/chromium \
  && python3 --version \
  && uv --version \
  && chromium --version
RUN groupmod --non-unique --gid "$AGENT_GID" node \
  && usermod --non-unique --uid "$AGENT_UID" --gid "$AGENT_GID" --login agent --home /home/agent --move-home node
USER ${AGENT_UID}:${AGENT_GID}
WORKDIR /home/agent/workspace
ENTRYPOINT ["sleep", "infinity"]
