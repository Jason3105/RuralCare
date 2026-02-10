"""
Prescription PDF Verification Module
Handles verification of uploaded prescription PDFs against blockchain-stored hashes
"""
import hashlib
import io
import logging
from typing import Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)


def compute_pdf_hash(pdf_content: bytes) -> str:
    """Compute SHA-256 hash of PDF content"""
    return hashlib.sha256(pdf_content).hexdigest()


def extract_pdf_content(pdf_file) -> bytes:
    """Extract raw bytes from uploaded PDF file"""
    if hasattr(pdf_file, 'read'):
        pdf_file.seek(0)
        content = pdf_file.read()
        pdf_file.seek(0)
        return content
    return pdf_file


def detect_if_scanned(pdf_file) -> Tuple[bool, Dict[str, Any]]:
    """
    Detect if PDF is a scanned document (primarily images vs text).
    
    Returns:
        Tuple of (is_scanned, details)
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF not installed. Install with: pip install PyMuPDF")
        return False, {'error': 'PyMuPDF not installed'}
    
    try:
        pdf_content = extract_pdf_content(pdf_file)
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        total_pages = len(doc)
        image_pages = 0
        total_text_length = 0
        total_images = 0
        
        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text()
            images = page.get_images()
            
            total_text_length += len(text.strip())
            total_images += len(images)
            
            # If page has very little text and at least one image, it's likely scanned
            if len(text.strip()) < 100 and len(images) > 0:
                image_pages += 1
        
        doc.close()
        
        # PDF is considered scanned if:
        # - More than 50% of pages are image-heavy with little text
        # - OR average text per page is very low but has images
        is_scanned = (
            (image_pages / max(total_pages, 1)) > 0.5 or 
            (total_text_length / max(total_pages, 1) < 200 and total_images > 0)
        )
        
        return is_scanned, {
            'total_pages': total_pages,
            'image_heavy_pages': image_pages,
            'total_images': total_images,
            'avg_text_per_page': total_text_length / max(total_pages, 1)
        }
        
    except Exception as e:
        logger.error(f"Error detecting scanned PDF: {e}")
        return False, {'error': str(e)}


def extract_text_from_pdf(pdf_file) -> Tuple[str, Dict[str, Any]]:
    """
    Extract text from PDF, with OCR fallback for scanned documents.
    
    Returns:
        Tuple of (extracted_text, details)
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return "", {'error': 'PyMuPDF not installed'}
    
    try:
        pdf_content = extract_pdf_content(pdf_file)
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        all_text = []
        extraction_method = 'text'
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            if text.strip():
                all_text.append(text)
            else:
                # Try OCR if available
                try:
                    # Get page as image and try OCR
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img_data = pix.tobytes("png")
                    
                    # Try pytesseract OCR
                    try:
                        import pytesseract
                        from PIL import Image
                        
                        img = Image.open(io.BytesIO(img_data))
                        ocr_text = pytesseract.image_to_string(img)
                        if ocr_text.strip():
                            all_text.append(ocr_text)
                            extraction_method = 'ocr'
                    except ImportError:
                        logger.warning("pytesseract not available for OCR")
                        extraction_method = 'partial'
                        
                except Exception as ocr_error:
                    logger.warning(f"OCR failed for page {page_num}: {ocr_error}")
        
        doc.close()
        
        return "\n".join(all_text), {
            'method': extraction_method,
            'pages_processed': len(doc) if doc else 0
        }
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return "", {'error': str(e)}


def extract_images_hash(pdf_file) -> str:
    """
    Extract all images from PDF and compute a combined hash.
    Useful for comparing scanned documents.
    """
    try:
        import fitz
    except ImportError:
        return ""
    
    try:
        pdf_content = extract_pdf_content(pdf_file)
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        image_hashes = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            images = page.get_images()
            
            for img_index, img in enumerate(images):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_data = base_image["image"]
                    img_hash = hashlib.sha256(image_data).hexdigest()[:16]
                    image_hashes.append(img_hash)
                except Exception:
                    continue
        
        doc.close()
        
        if image_hashes:
            combined = "".join(sorted(image_hashes))
            return hashlib.sha256(combined.encode()).hexdigest()
        return ""
        
    except Exception as e:
        logger.error(f"Error extracting images hash: {e}")
        return ""


def verify_prescription_pdf(uploaded_file, prescription) -> Dict[str, Any]:
    """
    Main verification function to verify an uploaded PDF against the original prescription.
    
    Args:
        uploaded_file: The uploaded PDF file object
        prescription: The Prescription model instance
        
    Returns:
        Dict with verification results:
        {
            'verified': bool,
            'method': 'exact_hash' | 'content_match' | 'failed',
            'hash_match': bool,
            'details': {...},
            'uploaded_hash': str,
            'original_hash': str,
            'warnings': [str],
            'is_scanned': bool
        }
    """
    result = {
        'verified': False,
        'method': 'unknown',
        'hash_match': False,
        'details': {},
        'uploaded_hash': '',
        'original_hash': prescription.pdf_hash or '',
        'warnings': [],
        'is_scanned': False
    }
    
    try:
        # Step 1: Get uploaded PDF content and compute hash
        pdf_content = extract_pdf_content(uploaded_file)
        uploaded_hash = compute_pdf_hash(pdf_content)
        result['uploaded_hash'] = uploaded_hash
        
        # Step 2: Direct hash comparison (exact match)
        if prescription.pdf_hash and uploaded_hash == prescription.pdf_hash:
            result['verified'] = True
            result['method'] = 'exact_hash'
            result['hash_match'] = True
            result['details'] = {'message': 'Document hash exactly matches the original'}
            return result
        
        # Step 3: Hash doesn't match - check if it's a scanned version
        is_scanned, scan_details = detect_if_scanned(uploaded_file)
        result['is_scanned'] = is_scanned
        result['details']['scan_info'] = scan_details
        
        if is_scanned:
            result['warnings'].append('This appears to be a scanned copy of the prescription')
            
            # For scanned documents, we can't do exact hash comparison
            # We'll extract text and check for key fields instead
            extracted_text, text_details = extract_text_from_pdf(uploaded_file)
            result['details']['extraction'] = text_details
            
            if extracted_text:
                # Check for key prescription fields in extracted text
                key_fields_found = 0
                total_key_fields = 0
                
                # Check patient name
                patient_name = f"{prescription.patient.first_name} {prescription.patient.last_name}"
                if patient_name.lower() in extracted_text.lower():
                    key_fields_found += 1
                total_key_fields += 1
                
                # Check doctor name
                doctor_name = f"{prescription.doctor.first_name} {prescription.doctor.last_name}"
                if doctor_name.lower() in extracted_text.lower():
                    key_fields_found += 1
                total_key_fields += 1
                
                # Check prescription ID
                if str(prescription.id) in extracted_text:
                    key_fields_found += 1
                total_key_fields += 1
                
                # Check for some medicine names
                for medicine in prescription.medicines.all()[:3]:  # Check first 3 medicines
                    total_key_fields += 1
                    if medicine.medicine_name.lower() in extracted_text.lower():
                        key_fields_found += 1
                
                match_percentage = (key_fields_found / max(total_key_fields, 1)) * 100
                result['details']['content_match'] = {
                    'key_fields_found': key_fields_found,
                    'total_key_fields': total_key_fields,
                    'match_percentage': round(match_percentage, 1)
                }
                
                if match_percentage >= 70:
                    result['verified'] = True
                    result['method'] = 'content_match'
                    result['warnings'].append(
                        f'Scanned document verified by content matching ({match_percentage:.0f}% key fields found). '
                        'Hash differs due to scanning process.'
                    )
                else:
                    result['verified'] = False
                    result['method'] = 'content_mismatch'
                    result['warnings'].append(
                        f'Document content does not match original prescription. '
                        f'Only {match_percentage:.0f}% of key fields found.'
                    )
            else:
                result['verified'] = False
                result['method'] = 'ocr_failed'
                result['warnings'].append('Could not extract text from scanned document for verification')
        else:
            # Not a scanned document, but hash doesn't match = tampered
            result['verified'] = False
            result['method'] = 'hash_mismatch'
            result['details']['message'] = 'Document hash does not match the original blockchain-verified hash'
            result['warnings'].append(
                'This document has been modified after the original was created. '
                'The hash fingerprint does not match the blockchain record.'
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Verification error: {e}")
        result['verified'] = False
        result['method'] = 'error'
        result['details'] = {'error': str(e)}
        result['warnings'].append(f'Verification failed due to an error: {str(e)}')
        return result


def get_prescription_by_id_from_pdf(pdf_file) -> Optional[str]:
    """
    Try to extract prescription ID from uploaded PDF.
    Looks for UUID in the Blockchain Verification section.
    
    Returns:
        Prescription UUID string if found, None otherwise
    """
    import re
    
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF not installed for prescription ID extraction")
        return None
    
    try:
        pdf_content = extract_pdf_content(pdf_file)
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        all_text = ""
        for page in doc:
            # Get text using different methods for better extraction
            text = page.get_text("text")
            all_text += text + " "
            
            # Also try block-based extraction for tables
            blocks = page.get_text("blocks")
            for block in blocks:
                if len(block) >= 5 and isinstance(block[4], str):
                    all_text += block[4] + " "
        
        doc.close()
        
        # Normalize text - remove extra whitespace and newlines
        normalized_text = " ".join(all_text.split())
        
        logger.debug(f"Extracted text length: {len(normalized_text)}")
        
        # Method 1: Look for "Prescription ID:" followed by UUID
        prescription_id_pattern = r'Prescription\s*ID[:\s]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
        id_match = re.search(prescription_id_pattern, normalized_text, re.IGNORECASE)
        if id_match:
            logger.info(f"Found prescription ID via label: {id_match.group(1)}")
            return id_match.group(1)
        
        # Method 2: Look for any UUID in the text (standard format)
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        matches = re.findall(uuid_pattern, normalized_text, re.IGNORECASE)
        if matches:
            # Return the first valid UUID found
            logger.info(f"Found prescription ID via UUID pattern: {matches[0]}")
            return matches[0]
        
        # Method 3: Try to find UUID that might have spaces/breaks in it
        # Sometimes PDFs break text across lines
        flexible_uuid_pattern = r'[0-9a-f]{8}\s*-\s*[0-9a-f]{4}\s*-\s*[0-9a-f]{4}\s*-\s*[0-9a-f]{4}\s*-\s*[0-9a-f]{12}'
        flexible_match = re.search(flexible_uuid_pattern, normalized_text, re.IGNORECASE)
        if flexible_match:
            # Clean up spaces from the match
            uuid_str = re.sub(r'\s+', '', flexible_match.group(0))
            logger.info(f"Found prescription ID via flexible pattern: {uuid_str}")
            return uuid_str
        
        logger.warning("No prescription ID found in PDF")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting prescription ID from PDF: {e}")
        return None

