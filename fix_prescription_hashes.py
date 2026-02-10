"""
Script to fix prescription hashes for existing prescriptions
This regenerates PDFs with QR codes and updates blockchain hashes
"""
import os
import django
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cancer_treatment_system.settings')
django.setup()

from patient_portal.prescription_models import Prescription
from patient_portal.prescription_pdf import generate_prescription_pdf
from blockchain.blockchain_service import store_prescription_hash
from django.conf import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_prescription_hashes():
    """Fix hashes for all prescriptions"""
    prescriptions = Prescription.objects.filter(pdf_file__isnull=False)
    
    logger.info(f"Found {prescriptions.count()} prescriptions to process")
    
    for prescription in prescriptions:
        try:
            logger.info(f"Processing prescription {prescription.id}")
            
            # Regenerate PDF with QR code
            pdf_file, pdf_hash = generate_prescription_pdf(prescription, include_qr=True)
            
            old_hash = prescription.pdf_hash
            logger.info(f"Old hash: {old_hash}")
            logger.info(f"New hash: {pdf_hash}")
            
            # Update prescription
            prescription.pdf_file = pdf_file
            prescription.pdf_hash = pdf_hash
            prescription.save()
            
            # Store new hash on blockchain
            if settings.BLOCKCHAIN_ENABLED and pdf_hash != old_hash:
                logger.info("Updating blockchain with new hash...")
                try:
                    result = store_prescription_hash(
                        prescription_id=prescription.id,
                        pdf_hash=pdf_hash,
                        patient_id=prescription.patient.id,
                        doctor_id=prescription.doctor.id
                    )
                    if result and result.get('success'):
                        prescription.blockchain_tx_hash = result['transaction_hash']
                        prescription.is_verified = True
                        prescription.save()
                        logger.info(f"✓ Updated on blockchain: {result['transaction_hash']}")
                    else:
                        logger.warning(f"Failed to update blockchain: {result}")
                except Exception as e:
                    logger.error(f"Blockchain error: {e}")
            
            logger.info(f"✓ Successfully processed prescription {prescription.id}\n")
            
        except Exception as e:
            logger.error(f"Error processing prescription {prescription.id}: {e}\n")
            continue
    
    logger.info("Done!")


if __name__ == '__main__':
    print("=" * 80)
    print("PRESCRIPTION HASH FIX UTILITY")
    print("=" * 80)
    print()
    print("This script will:")
    print("1. Regenerate PDFs for all prescriptions with QR codes")
    print("2. Update the pdf_hash field with the correct hash")
    print("3. Store the new hash on blockchain")
    print()
    response = input("Do you want to continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        fix_prescription_hashes()
    else:
        print("Cancelled.")
