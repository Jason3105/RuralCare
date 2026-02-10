"""
Deployment script for MedicalAccessLogger smart contract
"""
import json
import os
from web3 import Web3
from solcx import compile_standard, install_solc
from pathlib import Path

# Install specific Solidity compiler version
install_solc('0.8.19')

def deploy_contract():
    """Deploy MedicalAccessLogger contract to Sepolia testnet"""
    
    # Load configuration
    ALCHEMY_RPC_URL = os.getenv('ALCHEMY_RPC_URL', 'https://eth-sepolia.g.alchemy.com/v2/ZAE-pO0igQ8nXoQXUiylr')
    PRIVATE_KEY = os.getenv('BLOCKCHAIN_PRIVATE_KEY', '290493c95dfbcd38967f94a43bf16f4552abdf76ccfe4cc47652518963cf6bd8')
    
    # Connect to Sepolia via Alchemy
    w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC_URL))
    
    if not w3.is_connected():
        raise Exception("Failed to connect to Ethereum network")
    
    print(f"✓ Connected to Sepolia network")
    print(f"  Chain ID: {w3.eth.chain_id}")
    
    # Get account from private key
    account = w3.eth.account.from_key(PRIVATE_KEY)
    deployer_address = account.address
    
    print(f"✓ Deployer address: {deployer_address}")
    
    # Check balance
    balance = w3.eth.get_balance(deployer_address)
    balance_eth = w3.from_wei(balance, 'ether')
    print(f"✓ Account balance: {balance_eth} ETH")
    
    if balance == 0:
        print("\n⚠ WARNING: Account has no ETH. Get Sepolia testnet ETH from:")
        print("  - https://sepoliafaucet.com/")
        print("  - https://www.alchemy.com/faucets/ethereum-sepolia")
        return None
    
    # Read the contract source code
    contract_path = Path(__file__).parent.parent / 'contracts' / 'MedicalAccessLogger.sol'
    
    with open(contract_path, 'r') as file:
        contract_source_code = file.read()
    
    print(f"✓ Contract source loaded")
    
    # Compile the contract
    print("⏳ Compiling contract...")
    compiled_sol = compile_standard(
        {
            "language": "Solidity",
            "sources": {"MedicalAccessLogger.sol": {"content": contract_source_code}},
            "settings": {
                "outputSelection": {
                    "*": {
                        "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                    }
                }
            },
        },
        solc_version="0.8.19",
    )
    
    print("✓ Contract compiled successfully")
    
    # Get bytecode and ABI
    contract_interface = compiled_sol['contracts']['MedicalAccessLogger.sol']['MedicalAccessLogger']
    bytecode = contract_interface['evm']['bytecode']['object']
    abi = contract_interface['abi']
    
    # Save ABI to file
    abi_path = Path(__file__).parent.parent / 'contract_abi.json'
    with open(abi_path, 'w') as f:
        json.dump(abi, f, indent=2)
    
    print(f"✓ ABI saved to {abi_path}")
    
    # Create contract instance
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Get nonce
    nonce = w3.eth.get_transaction_count(deployer_address)
    
    # Build transaction
    print("⏳ Building deployment transaction...")
    transaction = Contract.constructor().build_transaction({
        'chainId': w3.eth.chain_id,
        'from': deployer_address,
        'nonce': nonce,
        'gas': 2000000,
        'gasPrice': w3.eth.gas_price,
    })
    
    # Sign transaction
    print("⏳ Signing transaction...")
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=PRIVATE_KEY)
    
    # Send transaction
    print("⏳ Deploying contract to Sepolia...")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    
    print(f"✓ Transaction sent: {tx_hash.hex()}")
    print(f"  View on Etherscan: https://sepolia.etherscan.io/tx/{tx_hash.hex()}")
    
    # Wait for transaction receipt
    print("⏳ Waiting for confirmation (this may take 15-30 seconds)...")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
    
    contract_address = tx_receipt.contractAddress
    
    print("\n" + "="*70)
    print("🎉 CONTRACT DEPLOYED SUCCESSFULLY!")
    print("="*70)
    print(f"Contract Address: {contract_address}")
    print(f"Transaction Hash: {tx_hash.hex()}")
    print(f"Block Number: {tx_receipt.blockNumber}")
    print(f"Gas Used: {tx_receipt.gasUsed}")
    print(f"\n📍 View on Etherscan:")
    print(f"   https://sepolia.etherscan.io/address/{contract_address}")
    print("="*70)
    
    # Save deployment info
    deployment_info = {
        'contract_address': contract_address,
        'transaction_hash': tx_hash.hex(),
        'block_number': tx_receipt.blockNumber,
        'deployer_address': deployer_address,
        'network': 'sepolia',
        'abi': abi
    }
    
    deployment_path = Path(__file__).parent.parent / 'deployment_info.json'
    with open(deployment_path, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    print(f"\n✓ Deployment info saved to {deployment_path}")
    print("\n📝 Next steps:")
    print("   1. Copy the contract address to your .env file")
    print("   2. Update BLOCKCHAIN_CONTRACT_ADDRESS in settings.py")
    print("   3. Restart your Django server")
    
    return deployment_info

if __name__ == '__main__':
    try:
        deploy_contract()
    except Exception as e:
        print(f"\n❌ Deployment failed: {str(e)}")
        import traceback
        traceback.print_exc()
