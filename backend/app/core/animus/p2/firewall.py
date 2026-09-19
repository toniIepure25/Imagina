"""ANIMUS-P2 test-set firewall.

Before the protocol is frozen, the confirmatory TEST partition's labels/outcomes must be inaccessible to
the training/selection process. Training may touch train+validation only. After the protocol seal is
committed (CI green), a distinct confirmatory command unlocks the test partition. This module provides a
software guard that records whether any test outcome was accessed before freeze (must be false).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass
class TestFirewall:
    seal_path: str
    _accessed_before_freeze: bool = False
    _accesses: list = field(default_factory=list)

    def is_frozen(self) -> bool:
        return os.path.exists(self.seal_path)

    def access_test(self, purpose: str):
        """Attempt to access the test partition. Allowed only after the protocol seal exists."""
        if not self.is_frozen():
            self._accessed_before_freeze = True
            self._accesses.append({"purpose": purpose, "allowed": False, "reason": "protocol not frozen"})
            raise PermissionError(
                f"test partition access '{purpose}' denied: protocol not frozen (firewall)")
        self._accesses.append({"purpose": purpose, "allowed": True})

    def guard_split(self, split: dict) -> dict:
        """Return train/val identities but withhold test identities until frozen."""
        out = {"train": split["train"], "val": split["val"]}
        if self.is_frozen():
            out["test"] = split["test"]
        else:
            out["test"] = "WITHHELD_UNTIL_FREEZE"
        return out

    def audit(self) -> dict:
        return {"protocol_frozen": self.is_frozen(),
                "test_outcome_accessed_before_freeze": self._accessed_before_freeze,
                "n_accesses": len(self._accesses), "accesses": self._accesses}


def write_audit(firewall: TestFirewall, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"artifact": "ANIMUS_P2_FIREWALL_AUDIT", **firewall.audit()}, f, indent=2)
