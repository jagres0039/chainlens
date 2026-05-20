"""ChainLens — risk scoring engine.
Pure rule-based scoring. LLM only adds narrative on top.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

Severity = Literal["low", "medium", "high", "critical"]


@dataclass
class Signal:
    """A single risk signal emitted by a detector."""
    code: str           # short id, e.g. "fresh_deploy"
    label: str          # human-readable, e.g. "Fresh deploy (3 days ago)"
    severity: Severity
    source: str         # "etherscan", "goplus", "rpc", "heuristic"
    detail: str = ""    # optional extra info


@dataclass
class RiskReport:
    address: str
    chain: str
    signals: list[Signal] = field(default_factory=list)
    risk_score: str = "Unknown"      # Low / Medium / High / Critical
    score_value: int = 0             # 0-100
    summary: str = ""                # LLM narrative (filled later)
    metadata: dict = field(default_factory=dict)
    latency_ms: int = 0

    def add(self, sig: Signal) -> None:
        self.signals.append(sig)


_SEVERITY_WEIGHT = {"low": 5, "medium": 15, "high": 30, "critical": 50}


def compute_risk(report: RiskReport) -> tuple[str, int]:
    """Aggregate signals into a final risk verdict + numeric score (0-100)."""
    if not report.signals:
        return "Unknown", 0
    total = sum(_SEVERITY_WEIGHT.get(s.severity, 0) for s in report.signals)
    score = min(100, total)
    if score >= 50:
        verdict = "Critical"
    elif score >= 30:
        verdict = "High"
    elif score >= 15:
        verdict = "Medium"
    else:
        verdict = "Low"
    return verdict, score
