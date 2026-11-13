# Linux worker runtime for the single-machine F09 recording profile.
# CPython 3.13.18 on Debian trixie; the digest is the 3.13-slim index of 2026-11-08.
FROM python:3.13.18-slim-trixie@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY worker-requirements.txt /opt/recording/worker-requirements.txt
# Every wheel is hash-pinned; no dependency resolution or source build is allowed.
RUN pip install --no-deps --only-binary=:all: --require-hashes \
        -r /opt/recording/worker-requirements.txt

# A fresh named evidence volume inherits this owner on first mount.
RUN mkdir /evidence && chown 10001:10001 /evidence
USER 10001:10001
WORKDIR /workspace
# -P keeps the working directory off sys.path; PYTHONPATH names the source mount.
ENTRYPOINT ["python", "-P", "-m"]
