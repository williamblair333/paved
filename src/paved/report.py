"""Structured results for probe/repair, with human and JSON rendering."""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field


@dataclass
class Diagnosis:
    """What a probe found about a file."""
    path: str
    container_ok: bool                 # top-level structure parses to EOF
    fault: str                         # machine code, e.g. "missing_mdat_header"
    detail: str                        # human explanation
    playable: bool | None = None       # decode-verify result (None = not run)
    boxes: list[str] = field(default_factory=list)  # top-level box types seen
    extra: dict = field(default_factory=dict)        # strategy hints (offsets, etc.)


@dataclass
class RepairResult:
    """Outcome of a repair attempt."""
    path: str
    output: str | None                 # path to repaired file, None if nothing written
    fault: str
    strategy: str | None               # strategy that produced a playable file
    success: bool                      # repaired file passes decode-verify
    lossy: bool                        # True if data was permanently lost
    lost: str                          # description of what was lost (empty if none)
    detail: str
    dry_run: bool = False

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def human(self) -> str:
        lines = [f"  file:     {self.path}"]
        lines.append(f"  fault:    {self.fault}")
        if self.dry_run:
            lines.append(f"  plan:     {self.detail}")
            lines.append("  dry-run:  no files written")
            return "\n".join(lines)
        if self.success:
            lines.append(f"  status:   REPAIRED via {self.strategy}")
            lines.append(f"  output:   {self.output}")
            if self.lossy:
                lines.append(f"  LOST:     {self.lost}  (permanently unrecoverable)")
            else:
                lines.append("  loss:     none — lossless repair")
        else:
            lines.append("  status:   FAILED — could not produce a playable file")
            lines.append(f"  detail:   {self.detail}")
        return "\n".join(lines)


def dumps(obj) -> str:
    if hasattr(obj, "to_dict"):
        obj = obj.to_dict()
    elif dataclasses.is_dataclass(obj):
        obj = dataclasses.asdict(obj)
    return json.dumps(obj, indent=2)
