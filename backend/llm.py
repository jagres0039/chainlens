"""LLM narrative — converts risk signals into a plain-English summary.

Supports two providers (configurable via env LLM_PROVIDER):
  - 9router: local OpenAI-compatible endpoint
  - openai:  hosted OpenAI API
  - none:    fallback rule-based summary (no LLM call)
"""
from __future__ import annotations
import os
import httpx

PROVIDER = os.environ.get("LLM_PROVIDER", "9router").lower()
NINEROUTER_BASE = os.environ.get("NINEROUTER_BASE_URL", "http://localhost:20128/v1")
NINEROUTER_KEY = os.environ.get("NINEROUTER_API_KEY", "")
NINEROUTER_MODEL = os.environ.get("NINEROUTER_MODEL", "jagrescombo")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def _rule_based_summary(report) -> str:
    """Fallback: build a summary from signals without calling an LLM."""
    if not report.signals:
        return f"This {report.metadata.get('type','address').lower()} has no notable risk signals based on automated checks. Always verify manually."

    crit = [s for s in report.signals if s.severity == "critical"]
    high = [s for s in report.signals if s.severity == "high"]
    med = [s for s in report.signals if s.severity == "medium"]

    parts = []
    if crit:
        parts.append(f"⚠️ Critical: {', '.join(s.label for s in crit[:2])}.")
    if high:
        parts.append(f"High-risk: {', '.join(s.label for s in high[:2])}.")
    if med:
        parts.append(f"Medium concerns: {', '.join(s.label for s in med[:2])}.")

    verdict_msg = {
        "Critical": "Do NOT interact. Strong indicators of malicious or scam contract.",
        "High": "High risk. Avoid signing or interacting unless you fully understand the code.",
        "Medium": "Medium risk. Review carefully before signing. Could be legitimate but speculative.",
        "Low": "Low risk based on automated scan. Still verify manually.",
        "Unknown": "Insufficient data to score risk.",
    }.get(report.risk_score, "")
    parts.append(verdict_msg)
    return " ".join(parts)


async def _call_9router(prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    if NINEROUTER_KEY:
        headers["Authorization"] = f"Bearer {NINEROUTER_KEY}"
    payload = {
        "model": NINEROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You are ChainLens, an on-chain risk explainer. Respond in 2-3 short sentences. Be concrete, no fluff, no disclaimers."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 200,
    }
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{NINEROUTER_BASE}/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


async def _call_openai(prompt: str) -> str:
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")
    headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": "You are ChainLens, an on-chain risk explainer. Respond in 2-3 short sentences. Be concrete, no fluff."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 200,
    }
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


async def narrate(report) -> str:
    """Generate a concise risk summary for a RiskReport."""
    if not report.signals:
        return _rule_based_summary(report)

    signals_text = "\n".join(f"- [{s.severity.upper()}] {s.label}" for s in report.signals[:10])
    prompt = (
        f"Address: {report.address}\n"
        f"Chain: {report.chain}\n"
        f"Type: {report.metadata.get('type','?')}\n"
        f"Risk verdict: {report.risk_score} (score {report.score_value}/100)\n\n"
        f"Detected signals:\n{signals_text}\n\n"
        f"Explain to a Web3 user what this address is and whether it's safe to interact with. "
        f"Be specific about the most dangerous signal first. Keep to 2-3 sentences."
    )
    try:
        if PROVIDER == "9router":
            return await _call_9router(prompt)
        if PROVIDER == "openai":
            return await _call_openai(prompt)
    except Exception:
        pass
    return _rule_based_summary(report)
