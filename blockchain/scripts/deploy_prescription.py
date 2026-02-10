"""
Deploy PrescriptionVerifier smart contract to Sepolia testnet
"""
import os
import json
import sys
from pathlib import Path
from web3 import Web3
from solcx import compile_standard, install_solc
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

def deploy_contract():
    """Deploy the PrescriptionVerifier contract to Sepolia"""
    
    # Load environment variables
    load_dotenv()
    
    print("\n" + "=" * 80)
    print("DEPLOYING PRESCRIPTION VERIFIER CONTRACT TO SEPOLIA")
    print("=" * 80)
    
    # Get configuration from environment
    rpc_url = os.getenv('ALCHEMY_RPC_URL')
    private_key = os.getenv('BLOCKCHAIN_PRIVATE_KEY')
    
    if not rpc_url or not private_key:
        print("\n❌ Error: Missing environment variables")
        print("Required: ALCHEMY_RPC_URL, BLOCKCHAIN_PRIVATE_KEY")
        return None
    
    # Connect to Sepolia
    print("\n🔗 Connecting to Sepolia testnet...")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print("❌ Failed to connect to Ethereum network")
        return None
    
    print(f"✓ Connected to Sepolia (Chain ID: {w3.eth.chain_id})")
    
    # Load account
    account = w3.eth.account.from_key(private_key)
    print(f"✓ Account loaded: {account.address}")
    
    # Check balance
    balance = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance, 'ether')
    print(f"✓ Account balance: {balance_eth:.6f} ETH")
    
    if balance == 0:
        print("\n⚠ WARNING: Account has no ETH. Get Sepolia testnet ETH from:")
        print("  - https://sepoliafaucet.com/")
        print("  - https://www.alchemy.com/faucets/ethereum-sepolia")
        return None
    
    # Read the contract source code
    contract_path = Path(__file__).parent.parent / 'contracts' / 'PrescriptionVerifier.sol'
    
    with open(contract_path, 'r') as file:
        contract_source_code = file.read()
    
    print(f"✓ Contract source loaded: PrescriptionVerifier.sol")
    
    # Install solc if needed
    try:
        print("⏳ Ensuring Solidity compiler is installed...")
        install_solc('0.8.19')
        print("✓ Solidity compiler ready")
    except Exception as e:
        print(f"⚠ Compiler installation info: {e}")
    
    # Compile the contract
    print("⏳ Compiling contract...")
    compiled_sol = compile_standard(
        {
            "language": "Solidity",
            "sources": {"PrescriptionVerifier.sol": {"content": contract_source_code}},
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
    contract_interface = compiled_sol['contracts']['PrescriptionVerifier.sol']['PrescriptionVerifier']
    bytecode = contract_interface['evm']['bytecode']['object']
    abi = contract_interface['abi']
    
    # Save ABI to file
    abi_path = Path(__file__).parent.parent / 'contract_abi.json'
    with open(abi_path, 'w') as f:
        json.dump(abi, f, indent=2)
    print(f"✓ ABI saved to: {abi_path}")
    
    # Create contract instance
    PrescriptionVerifier = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Get nonce
    nonce = w3.eth.get_transaction_count(account.address)
    print(f"✓ Account nonce: {nonce}")
    
    # Build deployment transaction with higher gas price
    print("\n🏗️  Building deployment transaction...")
    
    # Get current gas price and increase it by 3x for faster confirmation
    current_gas_price = w3.eth.gas_price
    boosted_gas_price = int(current_gas_price * 3)
    
    transaction = PrescriptionVerifier.constructor().build_transaction({
        'chainId': w3.eth.chain_id,
        'from': account.address,
        'nonce': nonce,
        'gas': 2000000,  # 2M gas limit
        'gasPrice': boosted_gas_price,
    })
    
    print(f"✓ Current network gas: {w3.from_wei(current_gas_price, 'gwei'):.2f} Gwei")
    print(f"✓ Using gas price: {w3.from_wei(transaction['gasPrice'], 'gwei'):.2f} Gwei (3x boost)")
    estimated_cost = w3.from_wei(transaction['gas'] * transaction['gasPrice'], 'ether')
    print(f"✓ Estimated deployment cost: {estimated_cost:.6f} ETH")
    
    # Sign transaction
    print("\n✍️  Signing transaction...")
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)
    print("✓ Transaction signed")
    
    # Send transaction
    print("\n📤 Sending transaction to network...")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    tx_hash_hex = tx_hash.hex()
    # Ensure 0x prefix
    if not tx_hash_hex.startswith('0x'):
        tx_hash_hex = '0x' + tx_hash_hex
    print(f"✓ Transaction sent: {tx_hash_hex}")
    print(f"📍 View on Etherscan: https://sepolia.etherscan.io/tx/{tx_hash_hex}")
    
    # Wait for receipt
    print("\n⏳ Waiting for transaction confirmation (this may take 30-60 seconds)...")
    try:
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        
        if tx_receipt.status == 1:
            contract_address = tx_receipt.contractAddress
            
            print("\n" + "=" * 80)
            print("🎉 DEPLOYMENT SUCCESSFUL!")
            print("=" * 80)
            print(f"\n📋 Contract Name: PrescriptionVerifier")
            print(f"📍 Contract Address: {contract_address}")
            print(f"🔗 View on Etherscan: https://sepolia.etherscan.io/address/{contract_address}")
            print(f"📝 Transaction Hash: {tx_hash_hex}")
            print(f"⛽ Gas Used: {tx_receipt.gasUsed:,}")
            print(f"🏦 Block Number: {tx_receipt.blockNumber}")
            
            # Save deployment info
            deployment_info = {
                'contract_name': 'PrescriptionVerifier',
                'contract_address': contract_address,
                'transaction_hash': tx_hash_hex,
                'block_number': tx_receipt.blockNumber,
                'deployer': account.address,
                'network': 'sepolia',
                'chain_id': w3.eth.chain_id,
                'gas_used': tx_receipt.gasUsed,
                'etherscan_url': f"https://sepolia.etherscan.io/address/{contract_address}"
            }
            
            deployment_path = Path(__file__).parent.parent / 'deployment_info.json'
            with open(deployment_path, 'w') as f:
                json.dump(deployment_info, f, indent=2)
            print(f"\n✓ Deployment info saved to: {deployment_path}")
            
            # Next steps
            print("\n" + "=" * 80)
            print("📋 NEXT STEPS:")
            print("=" * 80)
            print(f"\n1. Add this to your .env file:")
            print(f"   BLOCKCHAIN_CONTRACT_ADDRESS={contract_address}")
            print(f"\n2. Restart your Django server to load the new contract")
            print(f"\n3. Test prescription creation and blockchain verification")
            print("\n" + "=" * 80)
            
            return contract_address
        else:
            print(f"\n❌ Transaction failed! Status: {tx_receipt.status}")
            return None
            
    except Exception as e:
        print(f"\n❌ Error waiting for transaction: {str(e)}")
        print(f"Transaction may still be pending: https://sepolia.etherscan.io/tx/{tx_hash_hex}")
        return None


if __name__ == "__main__":
    try:
        contract_address = deploy_contract()
        if contract_address:
            print("\n✅ Deployment completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Deployment failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
