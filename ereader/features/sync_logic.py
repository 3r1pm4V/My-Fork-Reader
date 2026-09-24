"""Qt-free helpers for KOReader progress sync.

Kept separate from ``sync.py`` so the decision logic can be unit-tested
without PyQt and reused from the UI layer.
"""
from __future__ import annotations

from dataclasses import dataclass

# Only bother the user when local and remote differ by more than 0.5 %.
SYNC_TOLERANCE = 0.005


@dataclass(frozen=True)
class RemoteJump:
    percentage: float          # 0.0 - 1.0
    device: str                # name of the device that pushed it (may be "")
    cfi: str | None = None     # set only when remote 'progress' is a real EPUB CFI


def plan_remote_jump(remote, local_fraction: float,
                     tolerance: float = SYNC_TOLERANCE) -> RemoteJump | None:
    """Return a RemoteJump if the remote position is worth offering, else None.

    ``remote`` is the JSON dict returned by ``GET /syncs/progress/<hash>``.
    Returns None for: no/empty/malformed remote data, or a remote position
    within ``tolerance`` of the local one.
    """
    if not isinstance(remote, dict) or "percentage" not in remote:
        return None
    try:
        percentage = float(remote["percentage"])
    except (TypeError, ValueError):
        return None
    percentage = max(0.0, min(1.0, percentage))

    if abs(percentage - float(local_fraction or 0.0)) <= tolerance:
        return None

    # KOReader devices store an xpointer in 'progress', not an EPUB CFI.
    # Passing that to foliate's goTo() fails, so only trust real CFIs and
    # fall back to the percentage otherwise.
    progress = remote.get("progress")
    cfi = progress if isinstance(progress, str) and progress.startswith("epubcfi(") else None

    device = str(remote.get("device") or "")
    return RemoteJump(percentage=percentage, device=device, cfi=cfi)


__all__ = ["SYNC_TOLERANCE", "RemoteJump", "plan_remote_jump"]
