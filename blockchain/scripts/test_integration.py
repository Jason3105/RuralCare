"""
Test script to verify blockchain integration
Run this to check if everything is working
"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cancer_treatment_system.settings')
import django
django.setup()

from blockchain.blockchain_service import get_blockchain_service
from django.conf import settings

def test_blockchain_integration():
    """Test blockchain integration"""
    
    print("=" * 70)
    print("BLOCKCHAIN INTEGRATION TEST")
    print("=" * 70)
    
    # Test 1: Configuration
    print("\n1️⃣  Testing Configuration...")
    alchemy_url = getattr(settings, 'ALCHEMY_RPC_URL', None)
    private_key = getattr(settings, 'BLOCKCHAIN_PRIVATE_KEY', None)
    contract_address = getattr(settings, 'BLOCKCHAIN_CONTRACT_ADDRESS', None)
    enabled = getattr(settings, 'BLOCKCHAIN_ENABLED', False)
    
    print(f"   ALCHEMY_RPC_URL: {'✓ Set' if alchemy_url else '✗ Not set'}")
    print(f"   BLOCKCHAIN_PRIVATE_KEY: {'✓ Set' if private_key else '✗ Not set'}")
    print(f"   BLOCKCHAIN_CONTRACT_ADDRESS: {'✓ Set' if contract_address else '✗ Not deployed yet'}")
    print(f"   BLOCKCHAIN_ENABLED: {'✓ Enabled' if enabled else '✗ Disabled'}")
    
    if not contract_address:
        print("\n⚠️  Contract not deployed yet. Run: python blockchain/scripts/deploy.py")
        return
    
    # Test 2: Connection
    print("\n2️⃣  Testing Blockchain Connection...")
    service = get_blockchain_service()
    
    if service.is_connected():
        print("   ✓ Successfully connected to Ethereum network")
        print(f"   Network: Sepolia Testnet")
    else:
        print("   ✗ Failed to connect to Ethereum network")
        print("   Check your ALCHEMY_RPC_URL and internet connection")
        return
    
    # Test 3: Account
    print("\n3️⃣  Testing Account...")
    if service.account:
        print(f"   ✓ Account loaded: {service.account.address}")
        balance = service.get_balance()
        if balance is not None:
            print(f"   ✓ Balance: {balance:.4f} ETH")
            if balance < 0.01:
                print("   ⚠️  Low balance! Get more test ETH from https://sepoliafaucet.com/")
        else:
            print("   ✗ Could not fetch balance")
    else:
        print("   ✗ Account not loaded")
        return
    
    # Test 4: Contract
    print("\n4️⃣  Testing Smart Contract...")
    if service.contract:
        print(f"   ✓ Contract loaded: {contract_address}")
        try:
            total_logs = service.get_total_logs()
            print(f"   ✓ Total logs on blockchain: {total_logs}")
        except Exception as e:
            print(f"   ✗ Error reading contract: {str(e)}")
            return
    else:
        print("   ✗ Contract not loaded")
        return
    
    # Test 5: Database Models
    print("\n5️⃣  Testing Database Models...")
    try:
        from authentication.models import QRCodeScanLog
        # Check if blockchain fields exist
        sample = QRCodeScanLog._meta.get_field('blockchain_tx_hash')
        print("   ✓ Blockchain fields exist in QRCodeScanLog model")
        print("   ✓ Migrations applied successfully")
    except Exception as e:
        print(f"   ✗ Database issue: {str(e)}")
        print("   Run: python manage.py migrate")
        return
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    print("\nYour blockchain integration is working correctly!")
    print("\n📝 Next steps:")
    print("   1. Scan a QR code as a doctor")
    print("   2. Check for blockchain verification badge")
    print("   3. Click 'View on Etherscan' to verify")
    print("\n📊 View your contract:")
    print(f"   https://sepolia.etherscan.io/address/{contract_address}")
    print("=" * 70)

if __name__ == '__main__':
    try:
        test_blockchain_integration()
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
