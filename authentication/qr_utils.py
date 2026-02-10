"""
QR Code generation and validation utilities for Patient QR Access System
"""

import qrcode
import secrets
import hashlib
import logging
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils import timezone
from datetime import timedelta
from .models import PatientQRCode, QRCodeScanLog

logger = logging.getLogger(__name__)


def generate_encrypted_token():
    """
    Generate a secure, non-guessable encrypted token for patient QR code
    Uses cryptographically secure random generation
    """
    # Generate 32 random bytes and hash them
    random_bytes = secrets.token_bytes(32)
    token = hashlib.sha256(random_bytes).hexdigest()
    return token


def generate_qr_code(patient, token):
    """
    Generate QR code image from encrypted token
    
    Args:
        patient: User object (patient)
        token: Encrypted token string
    
    Returns:
        PIL Image object and saved file path
    """
    try:
        # Create QR code data
        qr_data = f"{token}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to file
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        
        # Create file content
        file_name = f'patient_qr_{patient.id}.png'
        file_content = ContentFile(img_io.getvalue(), name=file_name)
        
        return file_content, img
    
    except Exception as e:
        print(f"Error generating QR code: {str(e)}")
        return None, None


def create_patient_qr_code(patient, expires_in_days=365):
    """
    Create or update a patient's QR code
    
    Args:
        patient: User object (patient)
        expires_in_days: Number of days until QR code expires
    
    Returns:
        PatientQRCode object
    """
    try:
        # Check if QR code already exists (OneToOne relationship)
        try:
            qr_code = PatientQRCode.objects.get(patient=patient)
            # Return existing code
            return qr_code
        except PatientQRCode.DoesNotExist:
            pass
        
        # Generate encrypted token for new QR code
        token = generate_encrypted_token()
        
        # Create new QR code
        qr_code = PatientQRCode.objects.create(
            patient=patient,
            encrypted_token=token,
            expires_at=timezone.now() + timedelta(days=expires_in_days),
            status='active',
            is_active=True,
        )
        
        # Generate QR code image
        file_content, img = generate_qr_code(patient, token)
        
        if file_content:
            qr_code.qr_code_image.save(f'patient_qr_{patient.id}.png', file_content, save=True)
        
        return qr_code
    
    except Exception as e:
        print(f"Error creating patient QR code: {str(e)}")
        return None


def validate_qr_token(token):
    """
    Validate an encrypted QR code token
    
    Args:
        token: Encrypted token string
    
    Returns:
        PatientQRCode object if valid, None otherwise
    """
    try:
        qr_code = PatientQRCode.objects.get(
            encrypted_token=token,
            is_active=True,
            status='active'
        )
        
        # Check if expired
        if qr_code.is_expired():
            qr_code.status = 'expired'
            qr_code.save()
            return None
        
        return qr_code
    
    except PatientQRCode.DoesNotExist:
        return None


def log_qr_scan(qr_code, doctor, ip_address=None, user_agent=None, access_granted=True, denial_reason=None):
    """
    Log QR code scan event for audit trail and blockchain
    
    Args:
        qr_code: PatientQRCode object (can be None for failed scans)
        doctor: Doctor User object performing scan
        ip_address: IP address of scanning device
        user_agent: User agent string
        access_granted: Boolean indicating if access was granted
        denial_reason: Reason if access was denied
    
    Returns:
        QRCodeScanLog object
    """
    try:
        # Get patient from qr_code if available
        patient = qr_code.patient if qr_code else None
        
        scan_log = QRCodeScanLog.objects.create(
            qr_code=qr_code,
            patient=patient,
            scanned_by=doctor,
            ip_address=ip_address,
            user_agent=user_agent,
            access_granted=access_granted,
            denial_reason=denial_reason,
        )
        
        # Update QR code last scanned info (only if qr_code exists)
        if qr_code:
            qr_code.last_scanned_at = timezone.now()
            qr_code.last_scanned_by = doctor
            qr_code.save()
        
        # Log to blockchain asynchronously (non-blocking) - only for successful scans with valid patient
        if patient and qr_code:
            try:
                from django.conf import settings
                if getattr(settings, 'BLOCKCHAIN_ENABLED', False):
                    from blockchain.blockchain_service import get_blockchain_service
                    
                    blockchain_service = get_blockchain_service()
                    if blockchain_service.is_connected():
                        # Prepare metadata
                        metadata = {
                            'scan_type': 'qr_code',
                            'access_granted': access_granted,
                            'timestamp': str(timezone.now())
                        }
                        
                        # Log to blockchain
                        result = blockchain_service.log_qr_scan(
                            doctor_id=doctor.id,
                            patient_id=patient.id,
                            access_granted=access_granted,
                            metadata=metadata
                        )
                        
                        if result and result.get('success'):
                            # Save transaction hash immediately (even if pending)
                            scan_log.blockchain_tx_hash = result.get('transaction_hash')
                            
                            # Mark as verified if we have tx hash
                            if result.get('transaction_hash'):
                                scan_log.blockchain_verified = True
                            
                            # Add confirmed data if available
                            if not result.get('pending'):
                                scan_log.blockchain_log_id = result.get('log_id')
                                scan_log.blockchain_block_number = result.get('block_number')
                            
                            scan_log.save()
                            
                            status = "pending" if result.get('pending') else "confirmed"
                            logger.info(f"✓ Scan logged to blockchain ({status}): {result.get('transaction_hash')}")
                        else:
                            logger.warning(f"Failed to log to blockchain: {result.get('error') if result else 'Unknown error'}")
                    else:
                        logger.warning("Blockchain service not connected")
            except Exception as blockchain_error:
                # Don't fail the scan if blockchain logging fails
                logger.error(f"Blockchain logging error: {str(blockchain_error)}")
        
        return scan_log
    
    except Exception as e:
        print(f"Error logging QR scan: {str(e)}")
        return None


def regenerate_patient_qr_code(patient):
    """
    Regenerate patient's QR code (creates new token, invalidates old one)
    
    Args:
        patient: User object (patient)
    
    Returns:
        Updated PatientQRCode object with new token
    """
    try:
        qr_code = PatientQRCode.objects.get(patient=patient)
        
        # Generate new token
        new_token = generate_encrypted_token()
        
        # Update QR code with new token
        qr_code.encrypted_token = new_token
        qr_code.status = 'active'
        qr_code.is_active = True
        qr_code.regenerated_at = timezone.now()
        qr_code.expires_at = timezone.now() + timedelta(days=365)
        
        # Regenerate QR code image
        file_content, img = generate_qr_code(patient, new_token)
        if file_content:
            qr_code.qr_code_image.save(f'patient_qr_{patient.id}.png', file_content, save=True)
        else:
            qr_code.save()
        
        return qr_code
    
    except PatientQRCode.DoesNotExist:
        return create_patient_qr_code(patient)
    except Exception as e:
        print(f"Error regenerating QR code: {str(e)}")
        return None


def disable_patient_qr_code(patient):
    """
    Temporarily or permanently disable patient's QR code
    
    Args:
        patient: User object (patient)
    
    Returns:
        Boolean indicating success
    """
    try:
        PatientQRCode.objects.filter(patient=patient, is_active=True).update(
            is_active=False,
            status='inactive'
        )
        return True
    except Exception as e:
        print(f"Error disabling QR code: {str(e)}")
        return False


def enable_patient_qr_code(patient):
    """
    Re-enable patient's disabled QR code
    
    Args:
        patient: User object (patient)
    
    Returns:
        PatientQRCode object if successful, None otherwise
    """
    try:
        qr_code = PatientQRCode.objects.filter(patient=patient).first()
        if qr_code:
            qr_code.is_active = True
            qr_code.status = 'active'
            qr_code.save()
            return qr_code
        return None
    except Exception as e:
        print(f"Error enabling QR code: {str(e)}")
        return None
