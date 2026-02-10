"""
Update blockchain transaction status for pending scans
"""
import logging
from django.db import transaction
from authentication.models import QRCodeScanLog
from blockchain.blockchain_service import BlockchainService

logger = logging.getLogger(__name__)


def update_pending_transactions():
    """
    Check all pending blockchain transactions and update their status
    Returns: dict with update statistics
    """
    blockchain_service = BlockchainService()
    
    if not blockchain_service.connected:
        logger.error("Blockchain service not connected")
        return {'success': False, 'error': 'Blockchain service not connected'}
    
    # Get all scans with tx_hash but no block_number (pending)
    pending_scans = QRCodeScanLog.objects.filter(
        blockchain_tx_hash__isnull=False,
        blockchain_block_number__isnull=True
    ).order_by('-scan_timestamp')
    
    stats = {
        'success': True,
        'checked': 0,
        'confirmed': 0,
        'still_pending': 0,
        'failed': 0,
        'updated_scans': []
    }
    
    logger.info(f"Checking {pending_scans.count()} pending transactions...")
    
    for scan in pending_scans:
        stats['checked'] += 1
        
        try:
            # Ensure tx_hash has 0x prefix
            tx_hash = scan.blockchain_tx_hash
            if not tx_hash.startswith('0x'):
                tx_hash = f'0x{tx_hash}'
            
            # Try to get transaction receipt
            tx_receipt = blockchain_service.w3.eth.get_transaction_receipt(tx_hash)
            
            if tx_receipt:
                # Transaction is confirmed!
                if tx_receipt.status == 1:  # Success
                    # Parse logs to get logId
                    log_id = None
                    if tx_receipt.logs:
                        event_signature = blockchain_service.w3.keccak(text="AccessLogged(uint256,bytes32,bytes32,uint256,bool)")
                        for log in tx_receipt.logs:
                            if log.topics[0] == event_signature:
                                log_id = int.from_bytes(log.topics[1], byteorder='big')
                                break
                    
                    # Update database with confirmed data
                    with transaction.atomic():
                        scan.blockchain_block_number = tx_receipt.blockNumber
                        scan.blockchain_verified = True
                        if log_id:
                            scan.blockchain_log_id = log_id
                        scan.save(update_fields=['blockchain_block_number', 'blockchain_verified', 'blockchain_log_id'])
                    
                    stats['confirmed'] += 1
                    stats['updated_scans'].append({
                        'scan_id': scan.id,
                        'tx_hash': tx_hash,
                        'block_number': tx_receipt.blockNumber,
                        'log_id': log_id
                    })
                    logger.info(f"✓ Updated scan {scan.id} - Confirmed in block {tx_receipt.blockNumber}")
                else:
                    # Transaction failed
                    logger.warning(f"✗ Transaction {tx_hash} failed (status: {tx_receipt.status})")
                    stats['failed'] += 1
            else:
                # Still pending
                stats['still_pending'] += 1
                logger.debug(f"Transaction {tx_hash} still pending")
                
        except Exception as e:
            logger.error(f"Error checking transaction {scan.blockchain_tx_hash}: {str(e)}")
            stats['still_pending'] += 1
    
    logger.info(f"Update complete: {stats['confirmed']} confirmed, {stats['still_pending']} still pending, {stats['failed']} failed")
    return stats


def update_single_transaction(tx_hash):
    """
    Update status for a single transaction
    
    Args:
        tx_hash: Transaction hash (with or without 0x prefix)
        
    Returns:
        dict with update result
    """
    blockchain_service = BlockchainService()
    
    if not blockchain_service.connected:
        return {'success': False, 'error': 'Blockchain service not connected'}
    
    # Ensure tx_hash has 0x prefix
    if not tx_hash.startswith('0x'):
        tx_hash = f'0x{tx_hash}'
    
    # Find scan with this tx_hash
    try:
        # Try with 0x prefix
        scan = QRCodeScanLog.objects.filter(blockchain_tx_hash=tx_hash).first()
        if not scan:
            # Try without 0x prefix
            scan = QRCodeScanLog.objects.filter(blockchain_tx_hash=tx_hash[2:]).first()
        
        if not scan:
            return {'success': False, 'error': 'Transaction not found in database'}
        
        # Check if already confirmed
        if scan.blockchain_block_number:
            return {
                'success': True,
                'already_confirmed': True,
                'block_number': scan.blockchain_block_number,
                'message': 'Transaction already confirmed'
            }
        
        # Try to get transaction receipt
        tx_receipt = blockchain_service.w3.eth.get_transaction_receipt(tx_hash)
        
        if not tx_receipt:
            return {
                'success': True,
                'pending': True,
                'message': 'Transaction still pending confirmation'
            }
        
        if tx_receipt.status == 1:  # Success
            # Parse logs to get logId
            log_id = None
            if tx_receipt.logs:
                event_signature = blockchain_service.w3.keccak(text="AccessLogged(uint256,bytes32,bytes32,uint256,bool)")
                for log in tx_receipt.logs:
                    if log.topics[0] == event_signature:
                        log_id = int.from_bytes(log.topics[1], byteorder='big')
                        break
            
            # Update database
            with transaction.atomic():
                scan.blockchain_block_number = tx_receipt.blockNumber
                scan.blockchain_verified = True
                if log_id:
                    scan.blockchain_log_id = log_id
                scan.save(update_fields=['blockchain_block_number', 'blockchain_verified', 'blockchain_log_id'])
            
            return {
                'success': True,
                'confirmed': True,
                'block_number': tx_receipt.blockNumber,
                'log_id': log_id,
                'message': 'Transaction confirmed and updated'
            }
        else:
            return {
                'success': False,
                'failed': True,
                'message': f'Transaction failed (status: {tx_receipt.status})'
            }
            
    except Exception as e:
        logger.error(f"Error updating transaction {tx_hash}: {str(e)}")
        return {'success': False, 'error': str(e)}
