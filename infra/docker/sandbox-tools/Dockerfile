FROM python:3.12-alpine

WORKDIR /workspace

# Keep the image intentionally small and boring. The sandbox only supports
# explicit allowlisted helper commands, not a general shell environment.
RUN adduser -D -u 10001 sandbox \
    && mkdir -p /workspace \
    && chown sandbox:sandbox /workspace

USER sandbox
