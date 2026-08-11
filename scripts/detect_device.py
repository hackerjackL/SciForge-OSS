#!/usr/bin/env python3
"""Device/compute profiler (v1.4.0) — judge the box BEFORE choosing a backend.

SciForge is domain-agnostic: some domains need a GPU (deep learning), some a NPU
(Ascend), some only a CPU (symbolic / statistical / humanities).  There is no
"CPU-first" or "GPU-first" default — the *domain + box* decide.  This tool profiles
the machine at Phase 0/6 and emits a DEVICE profile that experiment-execution and
dynamic-sandbox consume to pick a backend, and that INSTALL/requirements use to
decide which optional compute extra to install.

Probes (no hard deps; torch is optional):
  - nvidia-smi      -> cuda   (+ device count / name)
  - rocminfo        -> rocm
  - npu-smi         -> npu    (Huawei Ascend)
  - torch.backends.mps -> mps (Apple Silicon)
  - otherwise       -> cpu

Usage:
  python scripts/detect_device.py            # print JSON to stdout
  python scripts/detect_device.py --out X    # also write X (e.g. .sciforge/DEVICE.json)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys


def _has(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _torch_info() -> dict:
    info = {"installed": False}
    try:
        import torch  # noqa: F401
    except Exception:
        return info
    info["installed"] = True
    info["version"] = getattr(torch, "__version__", "?")
    try:
        info["cuda_available"] = bool(torch.cuda.is_available())
        info["cuda_devices"] = torch.cuda.device_count() if info["cuda_available"] else 0
    except Exception:
        info["cuda_available"] = False
        info["cuda_devices"] = 0
    try:
        info["mps_available"] = bool(getattr(torch.backends, "mps", None)
                                     and torch.backends.mps.is_available())
    except Exception:
        info["mps_available"] = False
    try:
        import torch_npu  # noqa: F401
        info["npu_available"] = True
    except Exception:
        info["npu_available"] = False
    return info


def detect() -> dict:
    torch_info = _torch_info()
    if _has("nvidia-smi"):
        backend, tool = "cuda", "nvidia-smi"
    elif _has("rocminfo"):
        backend, tool = "rocm", "rocminfo"
    elif _has("npu-smi"):
        backend, tool = "npu", "npu-smi"
    elif torch_info.get("mps_available"):
        backend, tool = "mps", "torch.backends.mps"
    elif torch_info.get("cuda_available"):
        backend, tool = "cuda", "torch"
    elif torch_info.get("npu_available"):
        backend, tool = "npu", "torch_npu"
    else:
        backend, tool = "cpu", "none"
    return {
        "schema_version": "1.0",
        "backend": backend,
        "detector": tool,
        "torch": torch_info,
        "recommendation": {
            "cuda": "enable the torch (CUDA) compute extra; never hardcode .cuda()",
            "rocm": "install the ROCm torch build per INSTALL.md (not plain pip torch)",
            "npu": "install torch + torch_npu (Ascend) per INSTALL.md",
            "mps": "use the system torch with the MPS backend",
            "cpu": "no compute extra needed; CPU-only / humanities / symbolic runs",
        }[backend],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=str, default=None,
                    help="also write the DEVICE profile JSON to this path")
    args = ap.parse_args(argv)
    profile = detect()
    text = json.dumps(profile, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
