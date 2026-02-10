"""
Check transaction status and get contract address
"""
import os
from web3 import Web3
from dotenv import load_dotenv
import time

load_dotenv()

w3 = Web3(Web3.HTTPProvider(os.getenv('ALCHEMY_RPC_URL')))
tx_hash = '0x6ce9e5706059587db72bc9f3d585608902ae0d6973e9173724755ecca71df74d'

print(f"Checking transaction: {tx_hash}")
print(f"Etherscan: https://sepolia.etherscan.io/tx/{tx_hash}")
print("\nWaiting for confirmation...")

for i in range(60):  # Check for 5 minutes
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        if receipt:
            print(f"\n✓ Transaction confirmed!")
            print(f"Status: {'Success' if receipt.status == 1 else 'Failed'}")
            print(f"Contract Address: {receipt.contractAddress}")
            print(f"Block Number: {receipt.blockNumber}")
            print(f"Gas Used: {receipt.gasUsed:,}")
            
            if receipt.contractAddress:
                print(f"\n🎉 Contract deployed at: {receipt.contractAddress}")
                print(f"\nAdd this to your .env file:")
                print(f"BLOCKCHAIN_CONTRACT_ADDRESS={receipt.contractAddress}")
            break
    except Exception as e:
        pass
    
    print(f".", end="", flush=True)
    time.sleep(5)
else:
    print("\n\nTransaction still pending. Check Etherscan for status.")
    print(f"https://sepolia.etherscan.io/tx/{tx_hash}")
