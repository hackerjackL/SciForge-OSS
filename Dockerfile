# SciForge-OSS — headless runtime image (Linux, no GUI)
# GPU/NPU/CPU all work; figures + LaTeX + literature retrieval fully headless.
#   docker build -t sciforge .
#   docker run --rm -v $PWD:/work -w /work sciforge run --workspace /work/run --problem "..." --host manual
# Optional GPU: docker run --gpus all ...
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

# --- toolchain (texlive subset + figure engines + poppler) ---
RUN apt-get update && apt-get install -y --no-install-recommends \
      graphviz librsvg2-bin poppler-utils ca-certificates curl git \
      texlive-latex-base texlive-latex-recommended texlive-latex-extra \
      texlive-science texlive-publishers texlive-bibtex-extra latexmk \
    && rm -rf /var/lib/apt/lists/*

# --- d2 (primary diagram engine, headless-native) ---
RUN curl -fsSL https://d2lang.com/install.sh | sh -s -- || echo "d2 install skipped (offline build)"

# --- python arsenal (core; ML/torch added per-device at runtime) ---
WORKDIR /opt/sciforge
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# --- app ---
COPY . .
RUN pip install --no-cache-dir -e . 2>/dev/null || true

# non-root: kernel sandbox on Linux uses user namespaces (bwrap); --privileged or
# --cap-add=SYS_ADMIN + unprivileged usernsys on the host for sandboxed dispatch.
RUN useradd -m sciforge && chown -R sciforge /opt/sciforge
USER sciforge

# node for the sciforge npm CLI (kernel python is the control plane; JS bin is the wrapper)
RUN command -v node >/dev/null || echo "install node>=18 host-side or apt nodejs for the JS CLI entry"

ENTRYPOINT ["python", "-m", "sciforge.cli"]
CMD ["--help"]
