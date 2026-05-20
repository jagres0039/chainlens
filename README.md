<div align="center">

# 🔍 ChainLens

### *AI-Native On-Chain Risk Intelligence*

**Long-chain reasoning agent that turns raw blockchain data into safe-to-sign verdicts.**

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Live%20Demo-success.svg)]()

</div>

---

## 🎯 The Problem

Web3 retail users sign transactions they don't understand. Every week, **billions of dollars** are drained through:

- 🪤 **Honeypot tokens** that can be bought but never sold
- 🔓 **Hidden owner functions** (mint, blacklist, freeze)
- 🦠 **Fresh-deploy scams** dressed up to look like legit projects
- 🎭 **Proxy contracts** with upgradable malicious logic
- 💸 **Allowance abuse** via unlimited approve()

Reading Etherscan + GoPlus + Web3 RPC manually for every signature is **not realistic** for retail.

## 💡 The Solution

ChainLens is a **multi-stage AI reasoning pipeline** that compresses what would take a security analyst 30 minutes into a **3-second plain-English verdict**.

```
┌─────────────────────────────────────────────────────────────────┐
│                       LONG-CHAIN REASONING FLOW                  │
└─────────────────────────────────────────────────────────────────┘

  USER INPUT                    
   │ contract / wallet address                                     
   ▼                                                                
  ┌─────────────────┐                                              
  │ STAGE 1         │ ──┐                                          
  │ Data Ingestion  │   │ ┌──→ Etherscan v2 (verification, ABI)    
  │ (parallel)      │   ├─┼──→ GoPlus Security (risk flags)        
  │                 │   │ ├──→ Public RPC (bytecode, owner, calls) 
  │                 │   │ └──→ Token metadata + holder graph       
  └─────────────────┘ ──┘                                          
           │                                                        
           ▼                                                        
  ┌─────────────────┐    15+ specialist detectors run in parallel: 
  │ STAGE 2         │    • unverified source       • proxy upgrade 
  │ Risk Detection  │    • fresh deploy (<7d)      • owner mint    
  │ (rule engine)   │    • honeypot simulation     • blacklist     
  │                 │    • hidden owner            • high tax      
  │                 │    • whale concentration     • LP unlock     
  │                 │    • mint cap missing        • ownership renounce │
  └─────────────────┘                                              
           │                                                        
           ▼                                                        
  ┌─────────────────┐    Detector outputs aggregated into          
  │ STAGE 3         │    weighted risk vector with severity tags   
  │ Risk Synthesis  │    (CRITICAL / HIGH / MEDIUM / LOW / INFO)   
  │ (scoring engine)│                                              
  └─────────────────┘                                              
           │                                                        
           ▼                                                        
  ┌─────────────────┐    Claude Opus reads the full signal vector  
  │ STAGE 4         │    + raw on-chain context, then writes a     
  │ LLM Reasoning   │    coherent natural-language verdict that    
  │ (narrative)     │    explains *WHY* — not just *what*.         
  │                 │                                              
  │ Fallback chain: │    Why long-chain matters here: cross-       
  │ Claude → 9router│    referencing 15+ signals + bytecode + tx   
  │ → rule-based    │    pattern requires multi-step reasoning,    
  │                 │    not single-shot classification.           
  └─────────────────┘                                              
           │                                                        
           ▼                                                        
  ┌─────────────────┐                                              
  │ STAGE 5         │ →  JSON + UI card with:                      
  │ Verdict Output  │    • Risk Level (Low / Med / High / Critical)│
  │                 │    • 5-15 specific signals with severity     │
  │                 │    • 2-3 sentence plain-English summary      │
  │                 │    • Recommended action (sign / wait / skip) │
  └─────────────────┘                                              
```

This is **not a single LLM call**. It's a **5-stage agent loop** where each stage feeds context to the next, and the final reasoning step gets a structured signal vector — not raw noise — to write the verdict from.

---

## ✨ Features

### 🔍 Wallet Activity Explainer
Paste a wallet address and get a readable breakdown of recent claims, swaps, bridges, mints, and suspicious approvals across 6 EVM chains.

### 🛡️ NFT/Token Mint Risk Scanner
Parse contract fields, detect 15+ risk patterns, identify owner powers, and summarize whether a contract looks safe, weird, or worth avoiding.

### 📊 Composite Risk Score
Weighted scoring engine + LLM narrative layer combined into a single `Low / Medium / High / Critical` verdict with **5-15 specific signals per contract**.

### 🤖 Plain-English Reasoning
Claude Opus converts raw on-chain telemetry into a short, actionable risk summary in **<3 seconds** — no Etherscan reading required.

### 🔌 Builder-facing API
Clean REST API designed to be embedded in wallets, dashboards, or Telegram bots. JSON in, JSON out, no UI required.

### 🌐 Multi-Chain Coverage
Ethereum · Base · Arbitrum · Optimism · BSC · Polygon — all in one endpoint.

---

## 🎯 Production Targets

| Metric | Target | Achieved |
|---|---|---|
| Verdict latency (P50) | **3 seconds** | ✅ ~1.0s (CryptoPunks scan) |
| Risk signals per contract | **5+** | ✅ 15 detectors |
| Plain-English coverage | **100%** of outputs | ✅ |
| Supported chains | 6 EVMs | ✅ |
| Free-tier API only | No paid deps | ✅ |

---

## 🧱 Stack

| Layer | Tech |
|---|---|
| **Backend** | Python 3.11 · FastAPI · Web3.py · httpx |
| **AI Layer** | Claude Opus (primary) · 9router (local fallback) · rule-based (offline fallback) |
| **Agent Runtime** | Hermes Agent (orchestration + tool routing) |
| **Data Sources** | Etherscan v2 · GoPlus Security · publicnode.com RPC · blastapi.io fallback |
| **Frontend** | Vanilla HTML/CSS/JS — dark theme, no framework, fast load |
| **Cache** | In-memory + optional SQLite |
| **Deploy** | Cloudflare Tunnel · uvicorn · Docker-ready |

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/<your-username>/chainlens.git
cd chainlens

# 2. Install
pip install -r backend/requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env — add API keys (all free tier)

# 4. Run
uvicorn backend.main:app --host 0.0.0.0 --port 8080

# 5. Open
# Browse http://localhost:8080
```

---

## 📡 API

### `POST /api/scan/contract`

```bash
curl -X POST http://localhost:8080/api/scan/contract \
  -H "Content-Type: application/json" \
  -d '{
    "address": "0xb47e3cd837dDF8e4c57F05d70Ab865de6e193BBB",
    "chain": "ethereum"
  }'
```

**Response:**
```json
{
  "address": "0xb47e3cd837dDF8e4c57F05d70Ab865de6e193BBB",
  "chain": "ethereum",
  "risk_level": "Medium",
  "risk_score": 15,
  "signals": [
    {"name": "no_verified_source", "severity": "medium", "detail": "Source code not verified on Etherscan"},
    {"name": "proxy_contract", "severity": "low", "detail": "Upgradable proxy detected"},
    {"name": "high_holder_concentration", "severity": "medium", "detail": "Top 10 holders own 67%"}
  ],
  "summary": "CryptoPunks contract — verified ERC721 with strong holder distribution. Some signals require attention but no critical red flags.",
  "recommended_action": "review_before_sign",
  "latency_ms": 992
}
```

### `POST /api/scan/wallet`

```bash
curl -X POST http://localhost:8080/api/scan/wallet \
  -H "Content-Type: application/json" \
  -d '{
    "address": "0xabc...",
    "chain": "ethereum",
    "lookback_days": 30
  }'
```

Returns: classified breakdown of swaps, mints, approvals, bridges, claims with per-tx risk flags.

### `GET /api/health`

Returns: server status + LLM provider availability.

---

## 🎨 Risk Signals Library

| Signal | Source | Severity |
|---|---|---|
| Fresh deploy (<7 days) | Web3 + Etherscan | Medium |
| Unverified source code | Etherscan | Medium |
| Owner can mint unlimited | Contract bytecode | High |
| Hidden mint/burn functions | GoPlus | High |
| Honeypot (can't sell) | GoPlus simulation | Critical |
| Proxy upgradeable | Etherscan | Medium |
| Owner not renounced | Bytecode | Low |
| Anti-whale / blacklist | GoPlus | Medium |
| High tax (>10%) | GoPlus | High |
| Suspicious approval | Wallet scan | High |
| Liquidity unlock soon | DEX tools | Medium |
| High holder concentration | RPC | Medium |
| No social graph | Heuristic | Low |
| Sanctions match | OFAC list | Critical |
| Bytecode similarity to scam | Hash compare | High |

---

## 🗺 Roadmap

- [x] **EVM contract risk scanner** (15 detectors)
- [x] **Wallet activity explainer** (multi-chain)
- [x] **LLM narrative layer** (Claude Opus + fallbacks)
- [x] **Public live demo**
- [ ] Solana support
- [ ] Telegram bot (`/scan 0xabc...`)
- [ ] Browser extension (auto-scan before signing)
- [ ] API tier with auth + rate limits
- [ ] On-chain reputation graph
- [ ] Cross-tx behavior fingerprinting

---

## 🧠 Why "Long-Chain Reasoning"?

Traditional risk scanners do **single-pass classification**: pull data → run rules → output verdict. Easy to fool with proxy contracts, ownership renouncing tricks, or freshly verified shells.

ChainLens uses **multi-stage agent reasoning**:

1. **Hypothesis stage** — gather signals from independent sources (Etherscan + GoPlus + RPC) to triangulate, not just rely on one feed.
2. **Cross-reference stage** — does owner=address claim match bytecode? Does GoPlus honeypot flag align with allowance pattern? Conflicting signals get explicit treatment.
3. **Severity weighting stage** — rule engine produces a vector, not a binary.
4. **Narrative stage** — LLM gets the *full vector + raw context*, not just a yes/no, and writes verdict reasoning that a human can audit.
5. **Fallback chain** — if primary LLM fails, downgrade gracefully to rule-based summary so the system never returns blank.

This architecture is **why it catches edge cases** that single-shot scanners miss — and **why latency stays under 1s** despite querying 4+ data sources, because each stage runs concurrently where possible.

---

## 📜 License

MIT — see [LICENSE](LICENSE). No warranty. Nothing here constitutes financial advice.

---

## 🙏 Built With

- [Hermes Agent](https://hermes-agent.nousresearch.com) — agent runtime + tool orchestration
- [Etherscan](https://etherscan.io/apis) — verified source + ABI
- [GoPlus Security](https://gopluslabs.io/) — risk signal API
- [Web3.py](https://web3py.readthedocs.io/) — RPC + bytecode introspection
- [FastAPI](https://fastapi.tiangolo.com/) — async API framework
- [Claude](https://anthropic.com) — narrative reasoning layer

---

<div align="center">

**Built for users who want to understand *what they're signing*, not just *whether to sign*.**

</div>
