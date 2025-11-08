# app.py
import os
import sys
import json
import time
import argparse
from typing import Optional, Dict, Any
from web3 import Web3
from web3.exceptions import BadFunctionCallOutput, ContractLogicError

DEFAULT_RPC = os.environ.get("RPC_URL", "https://mainnet.infura.io/v3/YOUR_INFURA_KEY")

ERC20_MINIMAL_ABI = [
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
]

def to_checksum_or_die(addr: str) -> str:
    if not Web3.is_address(addr):
        raise ValueError(f"Invalid Ethereum address: {addr}")
    return Web3.to_checksum_address(addr)

def fetch_erc20_meta(contract) -> Dict[str, Any]:
    name, symbol, decimals = "Unknown", "???", 18
    try:
        name = contract.functions.name().call()
    except Exception:
        pass
    try:
        symbol = contract.functions.symbol().call()
    except Exception:
        pass
    try:
        decimals = contract.functions.decimals().call()
    except Exception:
        pass
    return {"name": name, "symbol": symbol, "decimals": decimals}

def get_allowance(contract, owner: str, spender: str, block_identifier: Optional[str] = "latest") -> int:
    try:
        return int(contract.functions.allowance(owner, spender).call(block_identifier=block_identifier))
    except (BadFunctionCallOutput, ContractLogicError) as e:
        raise RuntimeError(f"Allowance call failed (is this a valid ERC20?): {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch allowance: {e}")

def human_amount(amount_wei: int, decimals: int) -> str:
    if decimals <= 0:
        return str(amount_wei)
    fmt = f"{{:.{min(decimals, 18)}f}}"
    return fmt.format(amount_wei / (10 ** decimals))

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="zk-allowance-soundness — verify ERC20 allowance soundness for an owner→spender, optionally comparing to an expected value (useful for bridges, vaults, and zk systems like Aztec/Zama)."
    )
    p.add_argument("--rpc", default=DEFAULT_RPC, help="EVM RPC URL (default from RPC_URL)")
    p.add_argument("--token", required=True, help="ERC20 token address")
    p.add_argument("--owner", required=True, help="Owner address granting allowance")
    p.add_argument("--spender", required=True, help="Spender address receiving allowance")
    p.add_argument("--block", default="latest", help="Block tag/number (default: latest; try safe/finalized on L2s)")
    p.add_argument("--expected", type=str, help="Expected allowance in human units (e.g., 100.5). Optional.")
    p.add_argument("--timeout", type=int, default=30, help="RPC timeout seconds (default: 30)")
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return p.parse_args()

def main() -> None:
    start = time.time()
    args = parse_args()

    # RPC sanity
    if not args.rpc.startswith(("http://", "https://")):
        print("❌ Invalid RPC URL format. Must start with http(s).")
        sys.exit(1)

    # Address validation
    try:
        token = to_checksum_or_die(args.token)
        owner = to_checksum_or_die(args.owner)
        spender = to_checksum_or_die(args.spender)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(args.rpc, request_kwargs={"timeout": args.timeout}))
    if not w3.is_connected():
        print("❌ RPC connection failed. Check RPC_URL or --rpc.")
        sys.exit(1)

    contract = w3.eth.contract(address=token, abi=ERC20_MINIMAL_ABI)
    meta = fetch_erc20_meta(contract)

    print("🔧 zk-allowance-soundness")
    try:
        print(f"🧭 Chain ID: {w3.eth.chain_id}")
    except Exception:
        pass
    print(f"🔗 RPC: {args.rpc}")
    print(f"🧱 Block: {args.block}")
    print(f"🪙 Token: {meta['name']} ({meta['symbol']}) @ {token}")
    print(f"👤 Owner:  {owner}")
    print(f"🎯 Spender:{spender}")

    # Fetch allowance
    try:
        raw_allow = get_allowance(contract, owner, spender, block_identifier=args.block)
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(2)

    human_allow = human_amount(raw_allow, meta["decimals"])
    print(f"📦 Allowance (raw): {raw_allow}")
    print(f"💳 Allowance ({meta['symbol']}): {human_allow}")
#Warn if allowance is zero
    if raw_allow == 0:
        print("⚠️ Warning: Allowance is 0 — the spender cannot transfer tokens.")
        
    matched: Optional[bool] = None
    expected_raw: Optional[int] = None
    if args.expected is not None:
        try:
            # Parse expected in human units -> raw
            # Support decimals up to token's decimals
            exp_float = float(args.expected.replace(",", ""))
            expected_raw = int(round(exp_float * (10 ** meta["decimals"])))
            matched = (expected_raw == raw_allow)
            print(f"🎯 Expected: {args.expected} {meta['symbol']} (raw {expected_raw})")
            print("✅ MATCH" if matched else "❌ MISMATCH")
        except Exception as e:
            print(f"⚠️ Could not parse --expected '{args.expected}': {e}")

    elapsed = round(time.time() - start, 2)
    print(f"⏱️ Completed in {elapsed:.2f}s")

    if args.json:
        out = {
            "rpc": args.rpc,
            "chain_id": None,
            "token": token,
            "token_name": meta["name"],
            "token_symbol": meta["symbol"],
            "decimals": meta["decimals"],
            "owner": owner,
            "spender": spender,
            "block": args.block,
            "allowance_raw": raw_allow,
            "allowance_human": human_allow,
            "expected_human": args.expected,
            "expected_raw": expected_raw,
            "match": matched,
            "elapsed_seconds": elapsed,
        }
        try:
            out["chain_id"] = w3.eth.chain_id
        except Exception:
            pass
        print(json.dumps(out, ensure_ascii=False, indent=2))

    # Exit code: 0 on success / match-or-no-expected, 2 on mismatch or call failure handled above
    if matched is False:
        sys.exit(2)
    sys.exit(0)

if __name__ == "__main__":
    main()
