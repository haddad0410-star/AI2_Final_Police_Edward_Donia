"""Best-effort, never-fabricated hardware/environment detection for Step-0.

Every probe is wrapped so that an undeterminable value becomes ``None`` plus an
explanatory ``status`` string -- NEVER an invented number. GPU/VRAM in
particular is reported as ``None`` on a typical dev machine because there is no
reliable dependency-free probe, and inventing it is explicitly forbidden.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HardwareInfo:
    """A snapshot of the local machine, with per-field availability status.

    Field set frozen against `docs/schemas/declaration.schema.json`
    (session recovery step C, resolving risk #14) -- byte-identical to the
    Thief repo's `HardwareInfo`, including `vram_gb`/`vram_status`/
    `gpu_available`, which this dataclass previously lacked.
    """

    operating_system: str
    platform_detail: str
    python_version: str
    cpu_model: str | None
    cpu_model_status: str
    cpu_cores: int | None
    ram_gb: float | None
    ram_status: str
    gpu_model: str | None
    gpu_available: bool
    gpu_status: str
    vram_gb: float | None
    vram_status: str


def _detect_cpu_model() -> tuple[str | None, str]:
    """CPU brand string, best-effort per platform; ``None`` + status if unknown."""
    try:
        system = platform.system()
        if system == "Darwin":
            out = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=2,
                check=True,
            )
            value = out.stdout.strip()
            return (value, "detected") if value else (None, "empty sysctl result")
        if system == "Linux":
            for line in _read_proc_cpuinfo():
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip(), "detected"
        fallback = platform.processor()
        return (fallback, "detected") if fallback else (None, "unavailable on this platform")
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - env specific
        return None, f"probe failed: {exc}"


def _read_proc_cpuinfo() -> list[str]:  # pragma: no cover - Linux only
    with open("/proc/cpuinfo", encoding="utf-8") as handle:
        return handle.readlines()


def _detect_ram_gb() -> tuple[float | None, str]:
    """Physical RAM in GB via POSIX ``sysconf``; ``None`` + status otherwise."""
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        phys_pages = os.sysconf("SC_PHYS_PAGES")
        total_bytes = page_size * phys_pages
        return round(total_bytes / (1024**3), 2), "detected via sysconf"
    except (ValueError, OSError, AttributeError):  # pragma: no cover - non-POSIX
        return None, "unavailable: no POSIX sysconf RAM probe"


def probe_hardware() -> HardwareInfo:
    """Assemble a :class:`HardwareInfo`, never fabricating an unknown field."""
    cpu_model, cpu_status = _detect_cpu_model()
    ram_gb, ram_status = _detect_ram_gb()
    return HardwareInfo(
        operating_system=platform.system(),
        platform_detail=platform.platform(),
        python_version=sys.version.split()[0],
        cpu_model=cpu_model,
        cpu_model_status=cpu_status,
        cpu_cores=os.cpu_count(),
        ram_gb=ram_gb,
        ram_status=ram_status,
        gpu_model=None,
        gpu_available=False,
        gpu_status="not detected: no reliable dependency-free GPU probe (value never invented)",
        vram_gb=None,
        vram_status="not detected: no reliable dependency-free VRAM probe (value never invented)",
    )
