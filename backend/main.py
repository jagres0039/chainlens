"""ChainLens FastAPI backend."""
from __future__ import annotations
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from web3 import Web3

# Load .env from project root
ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

from . import scanner_contract, scanner_wallet, llm
from .onchain import CHAINS

app = FastAPI(title="ChainLens", version="0.1.0",
              description="AI × On-Chain Analysis — explain wallets, flag mint risk")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Models ----------

class ScanRequest(BaseModel):
    address: str = Field(..., description="0x... address (wallet or contract)")
    chain: str = Field("ethereum", description=f"Chain: {', '.join(CHAINS.keys())}")


class WalletScanRequest(ScanRequest):
    lookback_days: int = Field(30, ge=1, le=180)


# ---------- Helpers ----------

def _validate_address(addr: str) -> str:
    if not Web3.is_address(addr):
        raise HTTPException(400, f"Invalid address: {addr}")
    return Web3.to_checksum_address(addr)


def _validate_chain(chain: str) -> str:
    c = chain.lower()
    if c not in CHAINS:
        raise HTTPException(400, f"Unsupported chain: {chain}. Use: {list(CHAINS.keys())}")
    return c


def _serialize(report) -> dict:
    return {
        "address": report.address,
        "chain": report.chain,
        "risk_score": report.risk_score,
        "score_value": report.score_value,
        "signals": [
            {"code": s.code, "label": s.label, "severity": s.severity, "source": s.source, "detail": s.detail}
            for s in report.signals
        ],
        "summary": report.summary,
        "metadata": report.metadata,
        "latency_ms": report.latency_ms,
    }


# ---------- Routes ----------

@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "service": "ChainLens",
        "chains": list(CHAINS.keys()),
        "llm_provider": os.environ.get("LLM_PROVIDER", "9router"),
    }


@app.post("/api/scan/contract")
async def scan_contract_endpoint(req: ScanRequest):
    chain = _validate_chain(req.chain)
    address = _validate_address(req.address)
    started = time.time()
    report = await scanner_contract.scan_contract(chain, address)
    report.summary = await llm.narrate(report)
    report.latency_ms = int((time.time() - started) * 1000)
    return _serialize(report)


@app.post("/api/scan/wallet")
async def scan_wallet_endpoint(req: WalletScanRequest):
    chain = _validate_chain(req.chain)
    address = _validate_address(req.address)
    started = time.time()
    report = await scanner_wallet.scan_wallet(chain, address, req.lookback_days)
    report.summary = await llm.narrate(report)
    report.latency_ms = int((time.time() - started) * 1000)
    return _serialize(report)


@app.post("/api/scan")
async def scan_auto_endpoint(req: ScanRequest):
    """Auto-detect: if address is contract → run contract scan. If EOA → wallet scan."""
    chain = _validate_chain(req.chain)
    address = _validate_address(req.address)
    started = time.time()

    # Probe code length to decide
    from .onchain import get_code
    code = get_code(chain, address)
    is_contract = bool(code and code != "0x" and len(code) > 4)

    if is_contract:
        report = await scanner_contract.scan_contract(chain, address)
    else:
        report = await scanner_wallet.scan_wallet(chain, address, lookback_days=30)

    report.summary = await llm.narrate(report)
    report.latency_ms = int((time.time() - started) * 1000)
    return _serialize(report)


# ---------- Static frontend ----------

FRONTEND = ROOT / "frontend"
if FRONTEND.is_dir():
    @app.get("/", response_class=HTMLResponse)
    async def index():
        idx = FRONTEND / "index.html"
        if idx.is_file():
            return FileResponse(idx)
        return HTMLResponse("<h1>ChainLens</h1><p>frontend not built yet</p>")
    app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app",
                host=os.environ.get("HOST", "0.0.0.0"),
                port=int(os.environ.get("PORT", 8080)),
                reload=False)
