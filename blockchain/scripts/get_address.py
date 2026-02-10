"""
Script to get wallet address from private key
"""
from web3 import Web3
import os

PRIVATE_KEY = os.getenv('BLOCKCHAIN_PRIVATE_KEY', '290493c95dfbcd38967f94a43bf16f4552abdf76ccfe4cc47652518963cf6bd8')

w3 = Web3()
account = w3.eth.account.from_key(PRIVATE_KEY)

print("=" * 70)
print("WALLET INFORMATION")
print("=" * 70)
print(f"Address: {account.address}")
print(f"\nUse this address to get Sepolia test ETH from:")
print(f"  • https://sepoliafaucet.com/")
print(f"  • https://www.alchemy.com/faucets/ethereum-sepolia")
print("=" * 70)
