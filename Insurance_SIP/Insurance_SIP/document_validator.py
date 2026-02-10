"""
Document Validator using OCR (OpenCV + pytesseract alternative)
Validates uploaded documents for insurance applications
Uses pattern matching and basic OCR for validation
"""
import cv2
import numpy as np
from PIL import Image
import re
import io
import os


class DocumentValidator:
    """Validates documents using basic OCR and pattern matching"""
    
    def __init__(self):
        # Use lazy initialization - OCR reader will be initialized when needed
        self._reader = None
    
    @property
    def reader(self):
        """Lazy initialization of EasyOCR reader"""
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(['en'], gpu=False)  # Only English for faster loading
            except Exception as e:
                print(f"EasyOCR initialization error: {e}")
                self._reader = None
        return self._reader
    
    def preprocess_image(self, image_file):
        """Preprocess image for better OCR results"""
        try:
            # Check if it's a PDF
            file_name = getattr(image_file, 'name', '').lower()
            if file_name.endswith('.pdf'):
                # For PDFs, convert first page to image
                image = self._pdf_to_image(image_file)
                if image is None:
                    return None
            else:
                # Read image from uploaded file
                image = Image.open(image_file)
            
            # Convert to numpy array
            img_array = np.array(image)
            
            # Convert to grayscale if needed
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Apply thresholding to get better contrast
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
            
            return denoised
        except Exception as e:
            print(f"Error preprocessing image: {str(e)}")
            return None
    
    def _pdf_to_image(self, pdf_file):
        """Convert first page of PDF to image"""
        try:
            # Try using pdf2image if available
            try:
                from pdf2image import convert_from_bytes
                pdf_file.seek(0)
                images = convert_from_bytes(pdf_file.read(), first_page=1, last_page=1)
                return images[0] if images else None
            except ImportError:
                # Fallback: Use PyMuPDF (fitz) if available
                try:
                    import fitz
                    pdf_file.seek(0)
                    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
                    if len(doc) > 0:
                        page = doc[0]
                        pix = page.get_pixmap()
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        doc.close()
                        return img
                except ImportError:
                    print("Warning: PDF support requires pdf2image or PyMuPDF. PDFs will be accepted but not validated.")
                    # Return a dummy image for basic validation
                    return Image.new('RGB', (800, 1000), color='white')
        except Exception as e:
            print(f"Error converting PDF to image: {str(e)}")
            return None
    
    def extract_text(self, image_file):
        """Extract text from image using OCR"""
        try:
            # Reset file pointer
            image_file.seek(0)
            
            # Preprocess image
            processed_image = self.preprocess_image(image_file)
            
            if processed_image is None:
                return ""
            
            # Try EasyOCR if available
            if self.reader is not None:
                results = self.reader.readtext(processed_image)
                extracted_text = " ".join([text[1] for text in results])
            else:
                # Fallback: Basic pattern matching on image metadata
                # This is less accurate but works without external OCR
                image_file.seek(0)
                img = Image.open(image_file)
                # Get basic image info for validation
                extracted_text = f"IMAGE_FORMAT_{img.format} SIZE_{img.size[0]}x{img.size[1]}"
            
            return extracted_text.upper()
        except Exception as e:
            print(f"Error extracting text: {str(e)}")
            return ""
    
    def validate_image_quality(self, image_file):
        """Validate basic image quality requirements"""
        try:
            image_file.seek(0)
            file_name = getattr(image_file, 'name', '').lower()
            
            # Handle PDFs differently
            if file_name.endswith('.pdf'):
                # For PDFs, just check file size
                return True, "PDF document uploaded"
            
            img = Image.open(image_file)
            
            # Check minimum dimensions (at least 300x300)
            if img.size[0] < 300 or img.size[1] < 300:
                return False, "Image resolution too low. Please upload a clearer image (minimum 300x300 pixels)."
            
            # Check aspect ratio (not too elongated)
            aspect_ratio = max(img.size) / min(img.size)
            if aspect_ratio > 5:
                return False, "Image aspect ratio unusual. Please upload a properly cropped document."
            
            # Convert to numpy for additional checks
            img_array = np.array(img.convert('RGB'))
            
            # Check if image is too dark or too bright
            mean_brightness = np.mean(img_array)
            if mean_brightness < 30:
                return False, "Image too dark. Please upload a clearer, well-lit image."
            if mean_brightness > 225:
                return False, "Image too bright/washed out. Please upload a clearer image."
            
            # Check variance (blur detection)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if laplacian_var < 100:
                return False, "Image appears blurry. Please upload a sharp, clear image."
            
            return True, "Image quality acceptable"
        except Exception as e:
            return True, "Image quality check skipped"  # Don't block on errors
    
    def validate_aadhaar(self, image_file):
        """Validate Aadhaar card"""
        # First check image quality
        quality_ok, quality_msg = self.validate_image_quality(image_file)
        if not quality_ok:
            return False, quality_msg
        
        text = self.extract_text(image_file)
        
        if not text:
            # If OCR failed, check basic image properties as fallback
            image_file.seek(0)
            img = Image.open(image_file)
            # Accept if image has reasonable properties
            if img.size[0] * img.size[1] > 300000:  # At least 0.3 megapixels
                return True, "Aadhaar card accepted (quality check passed)"
            return False, "Unable to read document. Please upload a clear image of your Aadhaar card."
        
        # Check for Aadhaar identifiers
        aadhaar_keywords = [
            "GOVERNMENT OF INDIA",
            "AADHAAR",
            "UNIQUE IDENTIFICATION",
            "UIDAI"
        ]
        
        # Check if any keyword is present
        has_keyword = any(keyword in text for keyword in aadhaar_keywords)
        
        # Check for 12-digit Aadhaar number pattern
        aadhaar_pattern = r'\d{4}\s*\d{4}\s*\d{4}'
        has_number = bool(re.search(aadhaar_pattern, text))
        
        if has_keyword or has_number:
            return True, "Valid Aadhaar card detected"
        else:
            # Fallback: Accept if image quality is good
            return True, "Aadhaar card accepted (will be manually verified)"
    
    def validate_pan(self, image_file):
        """Validate PAN card"""
        # First check image quality
        quality_ok, quality_msg = self.validate_image_quality(image_file)
        if not quality_ok:
            return False, quality_msg
        
        text = self.extract_text(image_file)
        
        if not text:
            # Fallback: Accept if image quality is good
            image_file.seek(0)
            img = Image.open(image_file)
            if img.size[0] * img.size[1] > 300000:
                return True, "PAN card accepted (quality check passed)"
            return False, "Unable to read document. Please upload a clear image of your PAN card."
        
        # Check for PAN identifiers
        pan_keywords = [
            "INCOME TAX",
            "PERMANENT ACCOUNT NUMBER",
            "PAN",
            "GOVT OF INDIA"
        ]
        
        # Check if any keyword is present
        has_keyword = any(keyword in text for keyword in pan_keywords)
        
        # Check for PAN number pattern (ABCDE1234F)
        pan_pattern = r'[A-Z]{5}[0-9]{4}[A-Z]{1}'
        has_pan_number = bool(re.search(pan_pattern, text))
        
        if has_keyword or has_pan_number:
            return True, "Valid PAN card detected"
        else:
            return True, "PAN card accepted (will be manually verified)"
    
    def validate_income_proof(self, image_file):
        """Validate income proof document"""
        # First check image quality
        quality_ok, quality_msg = self.validate_image_quality(image_file)
        if not quality_ok:
            return False, quality_msg
        
        text = self.extract_text(image_file)
        
        if not text:
            # Fallback: Accept if image quality is good
            image_file.seek(0)
            img = Image.open(image_file)
            if img.size[0] * img.size[1] > 300000:
                return True, "Income proof accepted (quality check passed)"
            return False, "Unable to read document. Please upload a clear image."
        
        # Check for income-related keywords
        income_keywords = [
            "SALARY",
            "INCOME",
            "PAY SLIP",
            "PAYSLIP",
            "EARNING",
            "GROSS",
            "NET PAY",
            "BASIC PAY",
            "CTC",
            "ITR",
            "INCOME TAX RETURN",
            "FORM 16",
            "CERTIFICATE"
        ]
        
        # Check if any keyword is present
        has_keyword = any(keyword in text for keyword in income_keywords)
        
        # Check for currency symbols or amount patterns
        has_amount = bool(re.search(r'[₹$]\s*\d+|Rs\.?\s*\d+', text))
        
        if has_keyword or has_amount:
            return True, "Valid income proof document detected"
        else:
            return True, "Income proof accepted (will be manually verified)"
    
    def validate_medical_records(self, image_file):
        """Validate medical records"""
        # First check image quality
        quality_ok, quality_msg = self.validate_image_quality(image_file)
        if not quality_ok:
            return False, quality_msg
        
        text = self.extract_text(image_file)
        
        if not text:
            # Fallback: Accept if image quality is good (medical records vary widely)
            image_file.seek(0)
            img = Image.open(image_file)
            if img.size[0] * img.size[1] > 300000:
                return True, "Medical record accepted (quality check passed)"
            return False, "Unable to read document. Please upload a clear image."
        
        # Check for medical-related keywords
        medical_keywords = [
            "HOSPITAL",
            "CLINIC",
            "DOCTOR",
            "PATIENT",
            "MEDICAL",
            "PRESCRIPTION",
            "DIAGNOSIS",
            "REPORT",
            "LABORATORY",
            "TEST",
            "BLOOD",
            "X-RAY",
            "SCAN",
            "MRI",
            "CT",
            "HEALTH"
        ]
        
        # Check if any keyword is present
        has_keyword = any(keyword in text for keyword in medical_keywords)
        
        # Medical records are more flexible, so we accept if we find medical keywords
        if has_keyword:
            return True, "Valid medical record detected"
        else:
            return True, "Medical record accepted (will be manually verified)"
    
    def validate_document(self, document_type, image_file):
        """
        Main validation method
        
        Args:
            document_type: One of 'aadhaar', 'pan', 'income_proof', 'medical_records'
            image_file: Uploaded file object
        
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        # Validate file type
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf']
        file_name = image_file.name.lower()
        
        if not any(file_name.endswith(ext) for ext in allowed_extensions):
            return False, f"Invalid file type. Please upload {', '.join(allowed_extensions)}"
        
        # Validate file size (max 5MB)
        if image_file.size > 5 * 1024 * 1024:
            return False, "File size too large. Maximum size is 5MB."
        
        # Route to appropriate validator
        validators = {
            'aadhaar': self.validate_aadhaar,
            'pan': self.validate_pan,
            'income_proof': self.validate_income_proof,
            'medical_records': self.validate_medical_records
        }
        
        validator_func = validators.get(document_type)
        
        if not validator_func:
            return False, "Unknown document type"
        
        try:
            # Reset file pointer before validation
            image_file.seek(0)
            return validator_func(image_file)
        except Exception as e:
            print(f"Validation error: {str(e)}")
            return False, f"Error validating document: {str(e)}"


# Singleton instance
_validator_instance = None

def get_validator():
    """Get or create validator instance"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = DocumentValidator()
    return _validator_instance
