"""Contract risk detectors — runs all rules against a contract address."""
from __future__ import annotations
from . import onchain
from .risk_engine import RiskReport, Signal, compute_risk


async def scan_contract(chain: str, address: str) -> RiskReport:
    report = RiskReport(address=address, chain=chain)

    # ---------- 1. Source code & deploy info ----------
    src = await onchain.get_contract_source(chain, address)
    creation = await onchain.get_contract_creation(chain, address)

    is_contract = bool(src.get("ContractName")) or bool(onchain.get_code(chain, address)[2:])

    if not is_contract:
        report.metadata["type"] = "EOA (wallet)"
        report.add(Signal(
            code="not_a_contract",
            label="Address is a wallet, not a contract",
            severity="low",
            source="rpc",
        ))
        verdict, score = compute_risk(report)
        report.risk_score = verdict
        report.score_value = score
        return report

    report.metadata["type"] = "Contract"
    report.metadata["contract_name"] = src.get("ContractName") or "Unknown"
    report.metadata["compiler"] = src.get("CompilerVersion") or "?"

    source_code = src.get("SourceCode") or ""
    if not source_code:
        report.add(Signal(
            code="unverified_source",
            label="No verified source code",
            severity="medium",
            source="etherscan",
            detail="Owners hide implementation behind unverified bytecode",
        ))

    if str(src.get("Proxy")) == "1" or "implementation" in (src.get("Implementation") or "").lower():
        report.add(Signal(
            code="proxy_upgradeable",
            label="Proxy / upgradeable contract",
            severity="medium",
            source="etherscan",
            detail="Owner can change logic at any time",
        ))

    # ---------- 2. Deploy age ----------
    block = creation.get("blockNumber")
    if block:
        days = onchain.get_block_age_days(chain, int(block))
        report.metadata["deploy_age_days"] = round(days, 1) if days >= 0 else None
        report.metadata["deployer"] = creation.get("contractCreator")
        if 0 <= days < 7:
            report.add(Signal(
                code="fresh_deploy",
                label=f"Fresh deploy ({days:.0f} days ago)",
                severity="medium",
                source="etherscan",
            ))
        elif 0 <= days < 1:
            report.add(Signal(
                code="brand_new",
                label="Deployed within last 24h",
                severity="high",
                source="etherscan",
            ))

    # ---------- 3. Source-code heuristics ----------
    sc_lower = source_code.lower()
    if source_code:
        if "function mint" in sc_lower and "onlyowner" in sc_lower:
            report.add(Signal(
                code="owner_can_mint",
                label="Owner can mint unlimited supply",
                severity="high",
                source="heuristic",
            ))
        if "selfdestruct" in sc_lower or "suicide" in sc_lower:
            report.add(Signal(
                code="self_destruct",
                label="Contract can self-destruct",
                severity="high",
                source="heuristic",
            ))
        if "blacklist" in sc_lower or "_blacklisted" in sc_lower:
            report.add(Signal(
                code="blacklist",
                label="Has blacklist function (can block sells)",
                severity="high",
                source="heuristic",
            ))
        if "pause" in sc_lower and "onlyowner" in sc_lower:
            report.add(Signal(
                code="pausable",
                label="Owner can pause contract (freeze trading)",
                severity="medium",
                source="heuristic",
            ))

    # ---------- 4. GoPlus token security ----------
    gp = await onchain.goplus_token_security(chain, address)
    if gp:
        if str(gp.get("is_honeypot")) == "1":
            report.add(Signal(
                code="honeypot",
                label="HONEYPOT — token cannot be sold",
                severity="critical",
                source="goplus",
            ))
        if str(gp.get("is_mintable")) == "1":
            report.add(Signal(
                code="mintable",
                label="Token supply is mintable",
                severity="high",
                source="goplus",
            ))
        if str(gp.get("hidden_owner")) == "1":
            report.add(Signal(
                code="hidden_owner",
                label="Contract has hidden owner",
                severity="high",
                source="goplus",
            ))
        if str(gp.get("can_take_back_ownership")) == "1":
            report.add(Signal(
                code="ownership_takeback",
                label="Renounced ownership can be reclaimed",
                severity="high",
                source="goplus",
            ))
        if str(gp.get("transfer_pausable")) == "1":
            report.add(Signal(
                code="transfer_pausable",
                label="Transfers can be paused",
                severity="medium",
                source="goplus",
            ))
        try:
            buy_tax = float(gp.get("buy_tax") or 0)
            sell_tax = float(gp.get("sell_tax") or 0)
            if buy_tax > 0.10 or sell_tax > 0.10:
                report.add(Signal(
                    code="high_tax",
                    label=f"High buy/sell tax (buy {buy_tax*100:.0f}% / sell {sell_tax*100:.0f}%)",
                    severity="high",
                    source="goplus",
                ))
        except (ValueError, TypeError):
            pass
        if str(gp.get("anti_whale_modifiable")) == "1":
            report.add(Signal(
                code="anti_whale_modifiable",
                label="Anti-whale limit can be modified by owner",
                severity="medium",
                source="goplus",
            ))
        # Holder concentration
        try:
            holder_count = int(gp.get("holder_count") or 0)
            if 0 < holder_count < 100:
                report.add(Signal(
                    code="few_holders",
                    label=f"Only {holder_count} holders — concentrated",
                    severity="medium",
                    source="goplus",
                ))
        except (ValueError, TypeError):
            pass
        report.metadata["goplus_raw"] = {k: v for k, v in gp.items() if not isinstance(v, (list, dict))}

    # ---------- 5. Address security ----------
    addr_sec = await onchain.goplus_address_security(chain, address)
    if addr_sec:
        flags_high = ["cybercrime", "money_laundering", "phishing_activities",
                      "blacklist_doubt", "stealing_attack", "fake_kyc",
                      "malicious_mining_activities", "darkweb_transactions"]
        for flag in flags_high:
            if str(addr_sec.get(flag)) == "1":
                report.add(Signal(
                    code=f"addr_{flag}",
                    label=f"Address flagged: {flag.replace('_', ' ')}",
                    severity="critical",
                    source="goplus",
                ))

    # ---------- Final score ----------
    verdict, score = compute_risk(report)
    report.risk_score = verdict
    report.score_value = score
    return report
