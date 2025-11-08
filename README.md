# zk-allowance-soundness

## Overview
**zk-allowance-soundness** is a minimal CLI tool that checks ERC20 **allowance** soundness for an `owner → spender` pair at a given block.  
It’s handy for validating bridge/vault approvals, rollup agent permissions, and monitoring grant limits across EVM chains used by **Aztec**, **Zama**, and similar zk ecosystems.

## Installation
1) Python 3.9+  
2) Dependencies:
   pip install web3
3) RPC configuration:
   export RPC_URL=https://mainnet.infura.io/v3/YOUR_KEY  
   (or pass `--rpc` explicitly)

## Usage
Check allowance at latest block:
   python app.py --token 0xToken --owner 0xOwner --spender 0xSpender

Provide an expected value (human units):
   python app.py --token 0xToken --owner 0xOwner --spender 0xSpender --expected 1000

Use a specific block tag/number:
   python app.py --token 0xToken --owner 0xOwner --spender 0xSpender --block finalized
   python app.py --token 0xToken --owner 0xOwner --spender 0xSpender --block 21000000

JSON output for CI:
   python app.py --token 0xToken --owner 0xOwner --spender 0xSpender --json

## Parameters
--rpc        EVM RPC URL (default from env RPC_URL)  
--token      ERC20 token address (required)  
--owner      Owner address granting allowance (required)  
--spender    Spender address receiving allowance (required)  
--block      Block tag/number (default: latest)  
--expected   Expected allowance in human units (e.g., 1000.5)  
--timeout    RPC timeout seconds (default: 30)  
--json       Emit JSON summary

## Expected result
On success:
🔧 zk-allowance-soundness  
🧭 Chain ID: 1  
🔗 RPC: https://mainnet.infura.io/v3/…  
🧱 Block: latest  
🪙 Token: DAI (DAI) @ 0x6B…  
👤 Owner:  0xAb…  
🎯 Spender:0xCd…  
📦 Allowance (raw): 1000000000000000000000  
💳 Allowance (DAI): 1000.000000000000000000  
🎯 Expected: 1000 DAI (raw 1000000000000000000000)  
✅ MATCH  
⏱️ Completed in 0.41s

On mismatch:
❌ MISMATCH (exit code 2)

## Notes
- Human parsing of `--expected` uses the token’s `decimals`. For tokens with non-standard decimals, the tool reads them at runtime.  
- If the contract is not ERC20-compatible, the allowance call may revert; the tool will report an error and exit non-zero.  
- For proxy tokens, the allowance is read via the proxy address as exposed to users (standard ERC20 behavior).  
- Use stable block tags (`safe`, `finalized`) or a fixed block number for reproducible audits, especially on L2s.  
- Ideal for verifying Aztec bridges, Zama-integrated vaults, and any approvals relied upon by zk or cross-chain agents.  
- Exit codes: `0` on success/match (or when `--expected` omitted), `2` on mismatch or read failure.
