"""
Generate ABI file for MedicalAccessLogger contract
"""
import json
from pathlib import Path
from solcx import compile_standard, install_solc

def generate_abi():
    """Compile contract and generate ABI"""
    
    print("="*70)
    print("GENERATING MEDICALACCESSLOGGER ABI")
    print("="*70)
    
    # Install Solidity compiler
    try:
        print("⏳ Installing Solidity compiler 0.8.19...")
        install_solc('0.8.19')
        print("✓ Solidity compiler ready")
    except Exception as e:
        print(f"⚠ Compiler may already be installed: {e}")
    
    # Read the contract source code
    contract_path = Path(__file__).parent.parent / 'contracts' / 'MedicalAccessLogger.sol'
    
    with open(contract_path, 'r') as file:
        contract_source_code = file.read()
    
    print(f"✓ Contract source loaded from {contract_path}")
    
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
    
    # Extract ABI
    contract_interface = compiled_sol['contracts']['MedicalAccessLogger.sol']['MedicalAccessLogger']
    abi = contract_interface['abi']
    
    # Save ABI to medical_access_logger_abi.json
    abi_path = Path(__file__).parent.parent / 'medical_access_logger_abi.json'
    with open(abi_path, 'w') as f:
        json.dump(abi, f, indent=2)
    
    print(f"✓ ABI saved to {abi_path}")
    
    print("\n" + "="*70)
    print("✅ SUCCESS!")
    print("="*70)
    print(f"ABI file generated: medical_access_logger_abi.json")
    print(f"Contract address (from .env): 0xeb8AB8AC85b34dE49bcf26DD5651b35fdf19Cb0E")
    print("\nThe blockchain service will now be able to log QR scans to blockchain.")
    print("="*70)
    
    return abi

if __name__ == '__main__':
    try:
        generate_abi()
    except Exception as e:
        print(f"\n❌ Failed to generate ABI: {str(e)}")
        import traceback
        traceback.print_exc()
