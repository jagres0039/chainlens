"""Wallet activity classifier — turns raw txs into readable categories."""
from __future__ import annotations
import time
from . import onchain
from .risk_engine import RiskReport, Signal, compute_risk

# Common signature/method matches (4-byte selectors)
METHOD_HINTS = {
    "0xa9059cbb": ("transfer", "ERC-20 transfer"),
    "0x23b872dd": ("transferFrom", "ERC-20 transferFrom"),
    "0x095ea7b3": ("approve", "ERC-20 approve"),
    "0xd505accf": ("permit", "ERC-20 permit (gasless approve)"),
    "0x42842e0e": ("safeTransferFrom", "NFT transfer"),
    "0x40c10f19": ("mint", "Token/NFT mint"),
    "0xa0712d68": ("mint(uint256)", "NFT public mint"),
    "0x1249c58b": ("mint()", "Free mint"),
    "0xfb3bdb41": ("swapETHForExactTokens", "Uniswap-style swap (ETH→Token)"),
    "0x7ff36ab5": ("swapExactETHForTokens", "Uniswap-style swap (ETH→Token)"),
    "0x18cbafe5": ("swapExactTokensForETH", "Uniswap-style swap (Token→ETH)"),
    "0x38ed1739": ("swapExactTokensForTokens", "Uniswap-style swap (Token→Token)"),
    "0xb88d4fde": ("safeTransferFrom(NFT)", "NFT transfer with data"),
    "0x4f6ccce7": ("tokenByIndex", "NFT enumeration"),
    "0x2e1a7d4d": ("withdraw", "WETH unwrap / withdraw"),
    "0xd0e30db0": ("deposit", "WETH wrap / deposit"),
}


def _classify(tx: dict) -> tuple[str, str]:
    """Return (category, label) for a tx based on input data."""
    inp = (tx.get("input") or "").lower()
    if not inp or inp == "0x":
        # Plain ETH transfer
        return ("transfer", "Native transfer (ETH/BNB/etc)")
    sel = inp[:10]
    if sel in METHOD_HINTS:
        return METHOD_HINTS[sel]
    # Heuristics
    if "claim" in inp[:100]:
        return ("claim", "Token/airdrop claim")
    if "bridge" in inp[:100]:
        return ("bridge", "Cross-chain bridge")
    return ("contract_call", f"Contract call ({sel})")


async def scan_wallet(chain: str, address: str, lookback_days: int = 30) -> dict:
    """Build wallet activity breakdown."""
    started = time.time()
    cutoff = int(time.time()) - lookback_days * 86400

    txs = await onchain.get_tx_list(chain, address, page=1, offset=100)
    token_txs = await onchain.get_token_tx_list(chain, address, page=1, offset=100)

    # Filter to lookback window
    recent = [t for t in txs if int(t.get("timeStamp", 0)) >= cutoff]

    # Classify
    counts: dict[str, int] = {}
    notable: list[dict] = []
    approvals: list[dict] = []
    suspicious: list[Signal] = []

    for t in recent:
        cat, label = _classify(t)
        counts[cat] = counts.get(cat, 0) + 1
        if cat == "approve":
            approvals.append({
                "to": t.get("to"),
                "hash": t.get("hash"),
                "ts": int(t.get("timeStamp", 0)),
            })

    # Suspicious: approvals to unverified contracts
    if len(approvals) >= 5:
        suspicious.append(Signal(
            code="many_approvals",
            label=f"{len(approvals)} token approvals in last {lookback_days}d",
            severity="medium",
            source="heuristic",
            detail="High approval volume can mean wallet drainer exposure",
        ))

    # Bridges + multiple chain interactions
    if counts.get("bridge", 0) > 0:
        suspicious.append(Signal(
            code="bridging_activity",
            label=f"{counts['bridge']} bridge txs",
            severity="low",
            source="heuristic",
        ))

    # Address security check
    addr_sec = await onchain.goplus_address_security(chain, address)
    if addr_sec:
        for flag in ["cybercrime", "phishing_activities", "blacklist_doubt",
                     "stealing_attack", "darkweb_transactions"]:
            if str(addr_sec.get(flag)) == "1":
                suspicious.append(Signal(
                    code=f"addr_{flag}",
                    label=f"Address flagged: {flag.replace('_',' ')}",
                    severity="critical",
                    source="goplus",
                ))

    # Top counterparties
    counterparties: dict[str, int] = {}
    for t in recent:
        to = (t.get("to") or "").lower()
        if to and to != address.lower():
            counterparties[to] = counterparties.get(to, 0) + 1
    top_cps = sorted(counterparties.items(), key=lambda x: -x[1])[:5]

    # Build report
    report = RiskReport(address=address, chain=chain)
    for s in suspicious:
        report.add(s)
    verdict, score = compute_risk(report)
    report.risk_score = verdict
    report.score_value = score
    report.metadata = {
        "type": "EOA",
        "lookback_days": lookback_days,
        "tx_count": len(recent),
        "categories": counts,
        "approvals_count": len(approvals),
        "top_counterparties": [{"address": a, "count": c} for a, c in top_cps],
        "balance_native": onchain.get_balance(chain, address),
        "token_tx_count_30d": len([t for t in token_txs if int(t.get("timeStamp", 0)) >= cutoff]),
    }
    report.latency_ms = int((time.time() - started) * 1000)
    return report
