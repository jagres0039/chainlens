"""On-chain data adapters — Etherscan + GoPlus + public RPC."""
from __future__ import annotations
import os, time
from typing import Any

import httpx
from web3 import Web3

# Multi-chain Etherscan v2 API endpoints
ETHERSCAN_V2 = "https://api.etherscan.io/v2/api"
GOPLUS_BASE = "https://api.gopluslabs.io/api/v1"

CHAINS = {
    "ethereum":  {"chain_id": 1, "name": "Ethereum",
                  "rpcs": ["https://ethereum-rpc.publicnode.com",
                           "https://eth-mainnet.public.blastapi.io",
                           "https://ethereum.publicnode.com"]},
    "base":      {"chain_id": 8453, "name": "Base",
                  "rpcs": ["https://base-rpc.publicnode.com",
                           "https://base.blockpi.network/v1/rpc/public",
                           "https://mainnet.base.org"]},
    "arbitrum":  {"chain_id": 42161, "name": "Arbitrum",
                  "rpcs": ["https://arbitrum-one-rpc.publicnode.com",
                           "https://arb1.arbitrum.io/rpc"]},
    "optimism":  {"chain_id": 10, "name": "Optimism",
                  "rpcs": ["https://optimism-rpc.publicnode.com",
                           "https://mainnet.optimism.io"]},
    "bsc":       {"chain_id": 56, "name": "BSC",
                  "rpcs": ["https://bsc-rpc.publicnode.com",
                           "https://bsc-dataseed.binance.org"]},
    "polygon":   {"chain_id": 137, "name": "Polygon",
                  "rpcs": ["https://polygon-bor-rpc.publicnode.com",
                           "https://polygon-rpc.com"]},
}

ETHERSCAN_KEY = os.environ.get("ETHERSCAN_API_KEY", "")
GOPLUS_KEY = os.environ.get("GOPLUS_API_KEY", "")


def _w3(chain: str) -> Web3:
    cfg = CHAINS.get(chain.lower())
    if not cfg:
        raise ValueError(f"Unsupported chain: {chain}")
    # Try each RPC until one works
    last_err = None
    for rpc in cfg["rpcs"]:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 6}))
            w3.eth.block_number  # cheap probe
            return w3
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All RPCs failed for {chain}: {last_err}")


def chain_id(chain: str) -> int:
    return CHAINS[chain.lower()]["chain_id"]


# ---------- Etherscan ----------

async def etherscan_get(chain: str, params: dict) -> dict:
    """Generic Etherscan v2 API call. Returns empty result if no API key."""
    if not ETHERSCAN_KEY:
        return {"status": "0", "message": "no_api_key", "result": []}
    cid = chain_id(chain)
    q = {**params, "chainid": cid, "apikey": ETHERSCAN_KEY}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(ETHERSCAN_V2, params=q)
            r.raise_for_status()
            return r.json()
    except Exception:
        return {"status": "0", "message": "api_error", "result": []}


async def get_contract_source(chain: str, address: str) -> dict:
    """Returns {SourceCode, ContractName, ABI, IsProxy, ...} or empty dict."""
    j = await etherscan_get(chain, {
        "module": "contract", "action": "getsourcecode", "address": address,
    })
    res = (j.get("result") or [{}])[0]
    return res if isinstance(res, dict) else {}


async def get_contract_creation(chain: str, address: str) -> dict:
    """Returns {contractCreator, txHash, blockNumber, ...} or empty dict."""
    j = await etherscan_get(chain, {
        "module": "contract", "action": "getcontractcreation",
        "contractaddresses": address,
    })
    res = j.get("result") or []
    if isinstance(res, list) and res:
        return res[0]
    return {}


async def get_tx_list(chain: str, address: str, page: int = 1, offset: int = 50) -> list:
    """Recent normal transactions for a wallet."""
    j = await etherscan_get(chain, {
        "module": "account", "action": "txlist", "address": address,
        "startblock": 0, "endblock": 99999999, "page": page, "offset": offset,
        "sort": "desc",
    })
    res = j.get("result") or []
    return res if isinstance(res, list) else []


async def get_token_tx_list(chain: str, address: str, page: int = 1, offset: int = 50) -> list:
    """ERC-20 transfers for a wallet."""
    j = await etherscan_get(chain, {
        "module": "account", "action": "tokentx", "address": address,
        "startblock": 0, "endblock": 99999999, "page": page, "offset": offset,
        "sort": "desc",
    })
    res = j.get("result") or []
    return res if isinstance(res, list) else []


# ---------- GoPlus (free, no auth required for basic calls) ----------

async def goplus_token_security(chain: str, address: str) -> dict:
    """GoPlus token security check — returns dict of flags."""
    cid = chain_id(chain)
    url = f"{GOPLUS_BASE}/token_security/{cid}"
    params = {"contract_addresses": address.lower()}
    headers = {}
    if GOPLUS_KEY:
        headers["Authorization"] = GOPLUS_KEY
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(url, params=params, headers=headers)
        if r.status_code != 200:
            return {}
        j = r.json()
        result = j.get("result") or {}
        # GoPlus keys lowercase the address
        return result.get(address.lower(), {})


async def goplus_address_security(chain: str, address: str) -> dict:
    """GoPlus malicious address check."""
    cid = chain_id(chain)
    url = f"{GOPLUS_BASE}/address_security/{address}"
    params = {"chain_id": cid}
    headers = {}
    if GOPLUS_KEY:
        headers["Authorization"] = GOPLUS_KEY
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(url, params=params, headers=headers)
        if r.status_code != 200:
            return {}
        return (r.json().get("result") or {})


# ---------- RPC primitives ----------

def get_code(chain: str, address: str) -> str:
    return _w3(chain).eth.get_code(Web3.to_checksum_address(address)).hex()


def get_balance(chain: str, address: str) -> float:
    bal = _w3(chain).eth.get_balance(Web3.to_checksum_address(address))
    return float(Web3.from_wei(bal, "ether"))


def get_block_age_days(chain: str, block_number: int) -> float:
    """Approximate days since a block was mined."""
    w3 = _w3(chain)
    try:
        blk = w3.eth.get_block(int(block_number))
        return (time.time() - blk["timestamp"]) / 86400
    except Exception:
        return -1
