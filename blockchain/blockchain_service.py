"""
Blockchain service for logging and verifying QR code scans
"""
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from web3 import Web3
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class BlockchainService:
    """Service to interact with MedicalAccessLogger and PrescriptionVerifier smart contracts"""
    
    def __init__(self):
        """Initialize blockchain connection"""
        self.w3 = None
        self.contract = None
        self.prescription_contract = None
        self.account = None
        self.connected = False
        
        try:
            # Connect to Ethereum network
            rpc_url = getattr(settings, 'ALCHEMY_RPC_URL', None)
            if not rpc_url:
                logger.warning("ALCHEMY_RPC_URL not configured")
                return
            
            self.w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            if not self.w3.is_connected():
                logger.error("Failed to connect to Ethereum network")
                return
            
            # Load account
            private_key = getattr(settings, 'BLOCKCHAIN_PRIVATE_KEY', None)
            if not private_key:
                logger.warning("BLOCKCHAIN_PRIVATE_KEY not configured")
                return
            
            self.account = self.w3.eth.account.from_key(private_key)
            
            # Load QR code logging contract (MedicalAccessLogger)
            contract_address = getattr(settings, 'BLOCKCHAIN_CONTRACT_ADDRESS', None)
            if contract_address:
                # Try to load ABI for MedicalAccessLogger (if exists)
                abi_path = Path(__file__).parent / 'medical_access_logger_abi.json'
                if abi_path.exists():
                    with open(abi_path, 'r') as f:
                        abi = json.load(f)
                    
                    self.contract = self.w3.eth.contract(
                        address=Web3.to_checksum_address(contract_address),
                        abi=abi
                    )
                    logger.info(f"✓ MedicalAccessLogger contract loaded: {contract_address}")
                else:
                    logger.warning(f"MedicalAccessLogger ABI not found, QR logging disabled")
            
            # Load prescription verification contract (PrescriptionVerifier)
            prescription_contract_address = getattr(settings, 'PRESCRIPTION_CONTRACT_ADDRESS', None)
            if prescription_contract_address:
                # Load ABI for PrescriptionVerifier (contract_abi.json is for PrescriptionVerifier)
                abi_path = Path(__file__).parent / 'contract_abi.json'
                if abi_path.exists():
                    with open(abi_path, 'r') as f:
                        abi = json.load(f)
                    
                    self.prescription_contract = self.w3.eth.contract(
                        address=Web3.to_checksum_address(prescription_contract_address),
                        abi=abi
                    )
                    logger.info(f"✓ PrescriptionVerifier contract loaded: {prescription_contract_address}")
                else:
                    logger.error(f"PrescriptionVerifier ABI not found at {abi_path}")
            
            # Load consultation token verification contract (ConsultationTokenVerifier)
            self.token_contract = None
            token_contract_address = getattr(settings, 'CONSULTATION_TOKEN_CONTRACT_ADDRESS', None)
            if token_contract_address:
                abi_path = Path(__file__).parent / 'consultation_token_abi.json'
                if abi_path.exists():
                    with open(abi_path, 'r') as f:
                        abi = json.load(f)
                    
                    self.token_contract = self.w3.eth.contract(
                        address=Web3.to_checksum_address(token_contract_address),
                        abi=abi
                    )
                    logger.info(f"✓ ConsultationTokenVerifier contract loaded: {token_contract_address}")
                else:
                    logger.warning(f"ConsultationTokenVerifier ABI not found at {abi_path}")
            
            self.connected = True
            logger.info(f"✓ Blockchain service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize blockchain service: {str(e)}")
            self.connected = False
    
    def is_connected(self):
        """Check if blockchain service is connected"""
        return self.connected and self.w3 and self.w3.is_connected()
    
    def get_balance(self):
        """Get account ETH balance"""
        if not self.is_connected():
            return None
        
        try:
            balance_wei = self.w3.eth.get_balance(self.account.address)
            balance_eth = self.w3.from_wei(balance_wei, 'ether')
            return float(balance_eth)
        except Exception as e:
            logger.error(f"Error getting balance: {str(e)}")
            return None
    
    def _hash_identifier(self, identifier):
        """Create a hash of an identifier for privacy"""
        return self.w3.keccak(text=str(identifier))
    
    def log_qr_scan(self, doctor_id, patient_id, access_granted=True, metadata=None):
        """
        Log a QR code scan to the blockchain
        
        Args:
            doctor_id: Doctor's user ID
            patient_id: Patient's user ID  
            access_granted: Whether access was granted
            metadata: Optional metadata dict
            
        Returns:
            dict with transaction details or None if failed
        """
        if not self.is_connected():
            logger.warning("Blockchain not connected - scan not logged to blockchain")
            return None
        
        try:
            # Hash identifiers for privacy
            doctor_hash = self._hash_identifier(doctor_id)
            patient_hash = self._hash_identifier(patient_id)
            
            # Convert metadata to JSON string
            ipfs_metadata = json.dumps(metadata) if metadata else ""
            
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            # Estimate gas
            gas_estimate = self.contract.functions.logAccess(
                doctor_hash,
                patient_hash,
                access_granted,
                ipfs_metadata
            ).estimate_gas({'from': self.account.address})
            
            # Build transaction
            transaction = self.contract.functions.logAccess(
                doctor_hash,
                patient_hash,
                access_granted,
                ipfs_metadata
            ).build_transaction({
                'chainId': self.w3.eth.chain_id,
                'from': self.account.address,
                'nonce': nonce,
                'gas': int(gas_estimate * 1.2),  # Add 20% buffer
                'gasPrice': self.w3.eth.gas_price,
            })
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction, 
                private_key=self.account.key
            )
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            # Ensure tx_hash has 0x prefix for Etherscan
            tx_hash_hex = tx_hash.hex() if tx_hash.hex().startswith('0x') else f"0x{tx_hash.hex()}"
            logger.info(f"✓ QR scan transaction sent - TX: {tx_hash_hex}")
            
            # Return immediately with tx hash (don't wait for confirmation)
            result = {
                'success': True,
                'transaction_hash': tx_hash_hex,
                'pending': True,
                'explorer_url': f"https://sepolia.etherscan.io/tx/{tx_hash_hex}"
            }
            
            # Try to get receipt (with short timeout for quick response)
            try:
                tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=5)
                
                # Parse logs to get logId
                log_id = None
                if tx_receipt.logs:
                    # Decode the AccessLogged event
                    event_signature = self.w3.keccak(text="AccessLogged(uint256,bytes32,bytes32,uint256,bool)")
                    for log in tx_receipt.logs:
                        if log.topics[0] == event_signature:
                            # The logId is the first indexed parameter (topics[1])
                            log_id = int.from_bytes(log.topics[1], byteorder='big')
                            break
                
                # Update result with confirmed data
                result.update({
                    'pending': False,
                    'block_number': tx_receipt.blockNumber,
                    'log_id': log_id,
                    'gas_used': tx_receipt.gasUsed,
                    'confirmed': True
                })
                logger.info(f"✓ Transaction confirmed in block {tx_receipt.blockNumber}")
                
            except Exception as e:
                # Transaction sent but not yet confirmed - that's OK!
                logger.info(f"Transaction pending confirmation: {tx_hash_hex}")
                logger.warning(f"Transaction sent but receipt timeout: {str(e)}")
            
            # Return result (either confirmed or pending)
            return result
            
        except Exception as e:
            logger.error(f"Error logging to blockchain: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_access(self, log_id, doctor_id, patient_id):
        """
        Verify an access log on the blockchain
        
        Args:
            log_id: Blockchain log ID
            doctor_id: Doctor's user ID
            patient_id: Patient's user ID
            
        Returns:
            bool indicating if access is valid
        """
        if not self.is_connected():
            logger.warning("Blockchain not connected")
            return False
        
        try:
            doctor_hash = self._hash_identifier(doctor_id)
            patient_hash = self._hash_identifier(patient_id)
            
            is_valid = self.contract.functions.verifyAccess(
                log_id,
                doctor_hash,
                patient_hash
            ).call()
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying access: {str(e)}")
            return False
    
    def get_patient_scans(self, patient_id):
        """
        Get all blockchain log IDs for a patient
        
        Args:
            patient_id: Patient's user ID
            
        Returns:
            list of log IDs
        """
        if not self.is_connected():
            return []
        
        try:
            patient_hash = self._hash_identifier(patient_id)
            log_ids = self.contract.functions.getPatientLogs(patient_hash).call()
            return log_ids
        except Exception as e:
            logger.error(f"Error getting patient scans: {str(e)}")
            return []
    
    def get_doctor_scans(self, doctor_id):
        """
        Get all blockchain log IDs for a doctor
        
        Args:
            doctor_id: Doctor's user ID
            
        Returns:
            list of log IDs
        """
        if not self.is_connected():
            return []
        
        try:
            doctor_hash = self._hash_identifier(doctor_id)
            log_ids = self.contract.functions.getDoctorLogs(doctor_hash).call()
            return log_ids
        except Exception as e:
            logger.error(f"Error getting doctor scans: {str(e)}")
            return []
    
    def get_access_log(self, log_id):
        """
        Get access log details from blockchain
        
        Args:
            log_id: Blockchain log ID
            
        Returns:
            dict with log details
        """
        if not self.is_connected():
            return None
        
        try:
            log_data = self.contract.functions.getAccessLog(log_id).call()
            
            return {
                'doctor_hash': log_data[0].hex(),
                'patient_hash': log_data[1].hex(),
                'timestamp': log_data[2],
                'access_hash': log_data[3].hex(),
                'access_granted': log_data[4],
                'metadata': log_data[5]
            }
        except Exception as e:
            logger.error(f"Error getting access log: {str(e)}")
            return None
    
    def get_total_logs(self):
        """Get total number of logs on blockchain"""
        if not self.is_connected():
            return 0
        
        try:
            return self.contract.functions.getTotalLogs().call()
        except Exception as e:
            logger.error(f"Error getting total logs: {str(e)}")
            return 0
    
    def store_prescription_hash(self, prescription_id, pdf_hash, patient_id, doctor_id):
        """
        Store prescription PDF hash on blockchain for verification
        
        Args:
            prescription_id: ID of prescription (UUID or integer)
            pdf_hash: SHA-256 hash of PDF file (hex string)
            patient_id: Patient's user ID
            doctor_id: Doctor's user ID
            
        Returns:
            dict with transaction details or None if failed
        """
        if not self.is_connected() or not self.prescription_contract:
            logger.warning("Prescription contract not connected - prescription hash not stored")
            return None
        
        try:
            # Convert UUID to integer if needed
            if isinstance(prescription_id, str):
                # If it's a UUID string, convert to int
                import uuid as uuid_lib
                try:
                    prescription_uuid = uuid_lib.UUID(str(prescription_id))
                    prescription_id_int = prescription_uuid.int % (2**64)  # Use last 64 bits
                except ValueError:
                    # Not a UUID, try to convert directly
                    prescription_id_int = int(prescription_id)
            else:
                prescription_id_int = int(prescription_id)
            
            # Convert PDF hash from hex string to bytes32
            if isinstance(pdf_hash, str):
                if pdf_hash.startswith('0x'):
                    pdf_hash_bytes = bytes.fromhex(pdf_hash[2:])
                else:
                    pdf_hash_bytes = bytes.fromhex(pdf_hash)
                pdf_hash_bytes32 = self.w3.to_bytes(hexstr=pdf_hash)
            else:
                pdf_hash_bytes32 = pdf_hash
            
            # Hash identifiers for privacy
            doctor_hash = self._hash_identifier(doctor_id)
            patient_hash = self._hash_identifier(patient_id)
            
            # Create metadata
            metadata = json.dumps({
                'type': 'prescription',
                'prescription_id': str(prescription_id),  # Convert UUID to string
            })
            
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            # Estimate gas
            gas_estimate = self.prescription_contract.functions.storePrescription(
                pdf_hash_bytes32,
                doctor_hash,
                patient_hash,
                prescription_id_int,
                metadata
            ).estimate_gas({'from': self.account.address})
            
            # Build transaction with boosted gas for faster confirmation
            base_gas_price = self.w3.eth.gas_price
            boosted_gas_price = int(base_gas_price * 2)  # 2x gas price for faster confirmation
            
            transaction = self.prescription_contract.functions.storePrescription(
                pdf_hash_bytes32,
                doctor_hash,
                patient_hash,
                prescription_id_int,
                metadata
            ).build_transaction({
                'chainId': self.w3.eth.chain_id,
                'from': self.account.address,
                'nonce': nonce,
                'gas': int(gas_estimate * 1.5),  # Add 50% buffer for safety
                'gasPrice': boosted_gas_price,  # 2x base price for priority
            })
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction, 
                private_key=self.account.key
            )
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            # Ensure tx_hash has 0x prefix for Etherscan
            tx_hash_hex = tx_hash.hex() if tx_hash.hex().startswith('0x') else f"0x{tx_hash.hex()}"
            logger.info(f"✓ Prescription {prescription_id} hash storage transaction sent - TX: {tx_hash_hex}")
            
            # Return immediately with tx hash (don't wait for confirmation)
            result = {
                'success': True,
                'transaction_hash': tx_hash_hex,
                'pending': True,
                'explorer_url': f"https://sepolia.etherscan.io/tx/{tx_hash_hex}"
            }
            
            # Try to get receipt (with short timeout for quick response)
            try:
                tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=5)
                
                # Update result with confirmed data
                result.update({
                    'pending': False,
                    'block_number': tx_receipt.blockNumber,
                    'gas_used': tx_receipt.gasUsed,
                    'confirmed': True
                })
                logger.info(f"✓ Prescription transaction confirmed in block {tx_receipt.blockNumber}")
                
            except Exception as e:
                # Transaction sent but not yet confirmed - that's OK!
                logger.info(f"Prescription transaction pending confirmation: {tx_hash_hex}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error storing prescription hash on blockchain: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_prescription_hash(self, pdf_hash):
        """
        Verify if a prescription PDF hash exists on blockchain
        
        Args:
            pdf_hash: SHA-256 hash of PDF file (hex string)
            
        Returns:
            dict with verification details or None if not found
        """
        if not self.is_connected() or not self.prescription_contract:
            logger.warning("Prescription contract not connected")
            return None
        
        try:
            # Convert PDF hash from hex string to bytes32
            if isinstance(pdf_hash, str):
                if pdf_hash.startswith('0x'):
                    pdf_hash_bytes32 = self.w3.to_bytes(hexstr=pdf_hash)
                else:
                    pdf_hash_bytes32 = self.w3.to_bytes(hexstr='0x' + pdf_hash)
            else:
                pdf_hash_bytes32 = pdf_hash
            
            # Call verifyPrescription function
            exists, timestamp, prescription_id = self.prescription_contract.functions.verifyPrescription(
                pdf_hash_bytes32
            ).call()
            
            if exists:
                # Get full prescription details
                record = self.prescription_contract.functions.getPrescription(pdf_hash_bytes32).call()
                
                return {
                    'exists': True,
                    'prescription_id': prescription_id,
                    'timestamp': timestamp,
                    'doctor_hash': record[1].hex(),
                    'patient_hash': record[2].hex(),
                    'metadata': record[6] if len(record) > 6 else ''
                }
            else:
                return {
                    'exists': False
                }
                
        except Exception as e:
            logger.error(f"Error verifying prescription hash: {str(e)}")
            return None

    def store_token_hash(self, token_number, pdf_hash, patient_id, doctor_id):
        """
        Store consultation token PDF hash on blockchain for verification
        
        Args:
            token_number: Sequential token number for the doctor
            pdf_hash: SHA-256 hash of PDF file (hex string)
            patient_id: Patient's user ID
            doctor_id: Doctor's user ID
            
        Returns:
            dict with transaction details or None if failed
        """
        if not self.is_connected() or not self.token_contract:
            logger.warning("Token contract not connected - token hash not stored")
            return None
        
        try:
            # Convert PDF hash from hex string to bytes32
            if isinstance(pdf_hash, str):
                pdf_hash_bytes32 = self.w3.to_bytes(hexstr=('0x' + pdf_hash) if not pdf_hash.startswith('0x') else pdf_hash)
            else:
                pdf_hash_bytes32 = pdf_hash
            
            # Hash identifiers for privacy
            doctor_hash = self._hash_identifier(doctor_id)
            patient_hash = self._hash_identifier(patient_id)
            
            # Create metadata
            metadata = json.dumps({
                'type': 'consultation_token',
                'token_number': token_number,
            })
            
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            # Estimate gas
            gas_estimate = self.token_contract.functions.storeTokenHash(
                pdf_hash_bytes32,
                doctor_hash,
                patient_hash,
                token_number,
                metadata
            ).estimate_gas({'from': self.account.address})
            
            # Build transaction with boosted gas
            base_gas_price = self.w3.eth.gas_price
            boosted_gas_price = int(base_gas_price * 2)
            
            transaction = self.token_contract.functions.storeTokenHash(
                pdf_hash_bytes32,
                doctor_hash,
                patient_hash,
                token_number,
                metadata
            ).build_transaction({
                'chainId': self.w3.eth.chain_id,
                'from': self.account.address,
                'nonce': nonce,
                'gas': int(gas_estimate * 1.5),
                'gasPrice': boosted_gas_price,
            })
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction, 
                private_key=self.account.key
            )
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex() if tx_hash.hex().startswith('0x') else f"0x{tx_hash.hex()}"
            logger.info(f"✓ Token #{token_number} hash storage transaction sent - TX: {tx_hash_hex}")
            
            result = {
                'success': True,
                'transaction_hash': tx_hash_hex,
                'pending': True,
                'explorer_url': f"https://sepolia.etherscan.io/tx/{tx_hash_hex}"
            }
            
            # Try to get receipt
            try:
                tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=5)
                result.update({
                    'pending': False,
                    'block_number': tx_receipt.blockNumber,
                    'gas_used': tx_receipt.gasUsed,
                    'confirmed': True
                })
                logger.info(f"✓ Token transaction confirmed in block {tx_receipt.blockNumber}")
            except Exception as e:
                logger.info(f"Token transaction pending confirmation: {tx_hash_hex}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error storing token hash on blockchain: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_token_hash(self, pdf_hash):
        """
        Verify if a consultation token PDF hash exists on blockchain
        """
        if not self.is_connected() or not self.token_contract:
            logger.warning("Token contract not connected")
            return None
        
        try:
            if isinstance(pdf_hash, str):
                pdf_hash_bytes32 = self.w3.to_bytes(hexstr=('0x' + pdf_hash) if not pdf_hash.startswith('0x') else pdf_hash)
            else:
                pdf_hash_bytes32 = pdf_hash
            
            record = self.token_contract.functions.getTokenRecord(pdf_hash_bytes32).call()
            
            if record[5]:  # exists flag
                return {
                    'exists': True,
                    'token_number': record[4],
                    'timestamp': record[3],
                    'doctor_hash': record[1].hex(),
                    'patient_hash': record[2].hex(),
                    'metadata': record[6] if len(record) > 6 else ''
                }
            else:
                return {'exists': False}
                
        except Exception as e:
            logger.error(f"Error verifying token hash: {str(e)}")
            return None


# Singleton instance
_blockchain_service = None

def get_blockchain_service():
    """Get or create blockchain service singleton"""
    global _blockchain_service
    if _blockchain_service is None:
        _blockchain_service = BlockchainService()
    return _blockchain_service


def store_prescription_hash(prescription_id, pdf_hash, patient_id, doctor_id):
    """Convenience function to store prescription hash"""
    service = get_blockchain_service()
    return service.store_prescription_hash(prescription_id, pdf_hash, patient_id, doctor_id)


def store_consultation_token_hash(token_number, pdf_hash, patient_id, doctor_id):
    """Convenience function to store consultation token hash"""
    service = get_blockchain_service()
    return service.store_token_hash(token_number, pdf_hash, patient_id, doctor_id)
