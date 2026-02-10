"""
Medicine Image Analyzer using OpenCV and ML
Performs image preprocessing, text extraction (OCR), color analysis, and shape detection
Optimized for medicine packaging, tablets, syrups, and other pharmaceutical products
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import os
import re
from typing import Dict, List, Tuple, Optional
import tempfile


class MedicineImageAnalyzer:
    """
    OpenCV + ML based medicine image analyzer
    Extracts text, colors, shapes, and visual features from medicine images
    Uses multiple OCR strategies for maximum text extraction accuracy
    """
    
    def __init__(self):
        """Initialize the analyzer with Tesseract OCR and fallback options"""
        self.tesseract_available = False
        self.easyocr_available = False
        
        # Minimum confidence threshold for valid medicine image
        self.min_medicine_confidence = 0.3
        
        # Keywords that strongly indicate medicine-related content
        self.strong_medicine_indicators = [
            'mg', 'ml', 'mcg', 'tablet', 'tablets', 'tab', 'capsule', 'capsules', 'cap',
            'syrup', 'injection', 'cream', 'ointment', 'gel', 'lotion', 'drops',
            'dose', 'dosage', 'prescription', 'rx', 'pharma', 'pharmaceutical',
            'drug', 'medicine', 'medication', 'active ingredient', 'excipient',
            'manufactured by', 'mfg by', 'batch', 'lot', 'expiry', 'exp date',
            'for oral use', 'for external use', 'take as directed',
            'keep out of reach', 'store below', 'keep in cool',
            'paracetamol', 'ibuprofen', 'aspirin', 'antibiotic', 'antacid',
            'pain relief', 'fever', 'cold', 'cough', 'allergy',
        ]
        
        # Keywords that suggest non-medicine images
        self.non_medicine_indicators = [
            'restaurant', 'food', 'recipe', 'cooking', 'delicious',
            'fashion', 'clothing', 'wear', 'style',
            'selfie', 'portrait', 'vacation', 'travel', 'tourism',
            'animal', 'pet', 'dog', 'cat', 'bird',
            'car', 'vehicle', 'automobile', 'motorcycle',
            'landscape', 'nature', 'mountain', 'beach', 'sunset',
            'building', 'architecture', 'house', 'apartment',
            'electronics', 'phone', 'computer', 'laptop', 'gadget',
            'sports', 'game', 'player', 'team', 'score',
        ]
        
        # Initialize Tesseract OCR
        try:
            import pytesseract
            # Try to find tesseract executable
            if os.name == 'nt':  # Windows
                tesseract_paths = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                    r'C:\Tesseract-OCR\tesseract.exe',
                ]
                for path in tesseract_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        break
            self.pytesseract = pytesseract
            self.tesseract_available = True
            print("Tesseract OCR initialized successfully")
        except ImportError:
            print("Pytesseract not available")
        
        # Try to initialize EasyOCR as fallback
        try:
            import easyocr
            self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
            self.easyocr_available = True
            print("EasyOCR initialized successfully")
        except ImportError:
            print("EasyOCR not available - using Tesseract only")
        except Exception as e:
            print(f"EasyOCR initialization failed: {e}")
        
        # Common medicine-related keywords for text extraction
        self.medicine_keywords = [
            'mg', 'ml', 'mcg', 'tablet', 'tablets', 'tab', 'capsule', 'capsules', 'cap',
            'syrup', 'injection', 'cream', 'ointment', 'gel', 'lotion',
            'drops', 'spray', 'inhaler', 'powder', 'solution', 'suspension',
            'oral', 'topical', 'intravenous', 'subcutaneous',
            'dose', 'dosage', 'directions', 'warning', 'caution',
            'active', 'inactive', 'ingredients', 'contains', 'composition',
            'manufactured', 'mfg', 'exp', 'expiry', 'batch', 'lot',
            'store', 'storage', 'keep', 'refrigerate',
            'prescription', 'rx', 'otc', 'over-the-counter',
            'paracetamol', 'acetaminophen', 'ibuprofen', 'aspirin',
            'crocin', 'dolo', 'calpol', 'combiflam', 'disprin',
        ]
        
        # Common Indian medicine brand patterns
        self.brand_patterns = [
            r'\b(crocin|dolo|calpol|paracetamol)\b',
            r'\b(combiflam|brufen|ibuprofen)\b',
            r'\b(disprin|aspirin|ecosprin)\b',
            r'\b(amoxicillin|azithromycin|ciprofloxacin)\b',
            r'\b(metformin|glimepiride|vildagliptin)\b',
            r'\b(atorvastatin|rosuvastatin)\b',
            r'\b(omeprazole|pantoprazole|rabeprazole)\b',
            r'\b(cetirizine|loratadine|fexofenadine)\b',
            r'\b(montelukast|salbutamol|budesonide)\b',
        ]
        
        # Common medicine colors
        self.color_names = {
            'white': ([0, 0, 200], [180, 30, 255]),
            'red': ([0, 100, 100], [10, 255, 255]),
            'orange': ([10, 100, 100], [25, 255, 255]),
            'yellow': ([25, 100, 100], [35, 255, 255]),
            'green': ([35, 100, 100], [85, 255, 255]),
            'blue': ([85, 100, 100], [130, 255, 255]),
            'purple': ([130, 100, 100], [160, 255, 255]),
            'pink': ([160, 50, 100], [180, 255, 255]),
            'brown': ([10, 100, 50], [20, 255, 150]),
            'black': ([0, 0, 0], [180, 255, 50]),
        }
    
    def analyze_image(self, image_path: str) -> Dict:
        """
        Comprehensive analysis of medicine image using multiple techniques
        
        Args:
            image_path: Path to the medicine image
            
        Returns:
            Dictionary with extracted information
        """
        results = {
            'extracted_text': '',
            'cleaned_text': '',
            'detected_medicine_info': {},
            'visual_analysis': {},
            'ocr_confidence': 0.0,
            'processing_successful': False,
            'errors': [],
            'ocr_method_used': ''
        }
        
        try:
            # Load image with OpenCV
            image = cv2.imread(image_path)
            if image is None:
                # Try with PIL as fallback
                try:
                    pil_image = Image.open(image_path)
                    image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                except:
                    results['errors'].append("Failed to load image")
                    return results
            
            # Store original dimensions
            results['visual_analysis']['dimensions'] = {
                'width': int(image.shape[1]),
                'height': int(image.shape[0])
            }
            
            # Perform multi-engine text extraction
            text_results = self._extract_text_multi_engine(image, image_path)
            results['extracted_text'] = text_results['text']
            results['cleaned_text'] = text_results['cleaned_text']
            results['ocr_confidence'] = float(text_results['confidence'])
            results['ocr_method_used'] = text_results.get('method_used', 'unknown')
            
            # Extract medicine-specific information from text
            results['detected_medicine_info'] = self._extract_medicine_info(text_results['cleaned_text'])
            
            # Try to detect medicine brand from patterns
            detected_brand = self._detect_medicine_brand(text_results['cleaned_text'])
            if detected_brand:
                results['detected_medicine_info']['detected_brand'] = detected_brand
            
            # Visual analysis
            results['visual_analysis'].update(self._analyze_visual_features(image))
            
            # Detect medicine form (tablet, capsule, etc.)
            results['visual_analysis']['detected_form'] = self._detect_medicine_form(image, text_results['cleaned_text'])
            
            results['processing_successful'] = True
            
            # Validate if this is actually a medicine image
            validation_result = self._validate_medicine_image(results)
            results['is_valid_medicine_image'] = validation_result['is_valid']
            results['medicine_confidence_score'] = validation_result['confidence_score']
            results['validation_reason'] = validation_result['reason']
            results['validation_suggestions'] = validation_result.get('suggestions', [])
            
        except Exception as e:
            results['errors'].append(str(e))
            import traceback
            print(f"Image analysis error: {traceback.format_exc()}")
        
        return results
    
    def _detect_medicine_brand(self, text: str) -> Optional[str]:
        """Try to detect medicine brand from extracted text using patterns"""
        text_lower = text.lower()
        
        for pattern in self.brand_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(0).title()
        
        return None
    
    def _extract_text_multi_engine(self, image: np.ndarray, image_path: str) -> Dict:
        """
        Extract text using multiple OCR engines for maximum accuracy
        Tries Tesseract first, then EasyOCR as fallback
        """
        result = {
            'text': '',
            'cleaned_text': '',
            'confidence': 0.0,
            'method_used': ''
        }
        
        all_texts = []
        all_confidences = []
        
        # Strategy 1: Tesseract with multiple preprocessing
        if self.tesseract_available:
            tesseract_result = self._extract_text_tesseract(image)
            if tesseract_result['text']:
                all_texts.append(tesseract_result['text'])
                all_confidences.append(tesseract_result['confidence'])
                result['method_used'] = 'tesseract'
        
        # Strategy 2: EasyOCR (often better for stylized text)
        if self.easyocr_available:
            easyocr_result = self._extract_text_easyocr(image)
            if easyocr_result['text']:
                all_texts.append(easyocr_result['text'])
                all_confidences.append(easyocr_result['confidence'])
                if not result['method_used']:
                    result['method_used'] = 'easyocr'
                else:
                    result['method_used'] += '+easyocr'
        
        # Strategy 3: PIL-based preprocessing + Tesseract
        if self.tesseract_available:
            pil_result = self._extract_text_pil_preprocessing(image_path)
            if pil_result['text']:
                all_texts.append(pil_result['text'])
                all_confidences.append(pil_result['confidence'])
        
        # Combine all results
        if all_texts:
            # Merge and deduplicate
            combined_text = ' '.join(all_texts)
            result['text'] = combined_text
            result['cleaned_text'] = self._clean_extracted_text(combined_text)
            result['confidence'] = max(all_confidences) if all_confidences else 0.0
        
        return result
    
    def _extract_text_tesseract(self, image: np.ndarray) -> Dict:
        """Extract text using Tesseract with multiple preprocessing strategies"""
        result = {'text': '', 'confidence': 0.0}
        
        if not self.tesseract_available:
            return result
        
        all_texts = []
        confidences = []
        
        preprocessing_methods = [
            self._preprocess_default,
            self._preprocess_adaptive,
            self._preprocess_sharpen,
            self._preprocess_denoise,
            self._preprocess_resize_and_enhance,
            self._preprocess_morphological,
            self._preprocess_invert,
            self._preprocess_edge_enhance,
        ]
        
        psm_modes = [6, 3, 11, 4, 7, 8]  # Various page segmentation modes
        
        for preprocess_func in preprocessing_methods:
            try:
                processed = preprocess_func(image)
                
                for psm in psm_modes:
                    try:
                        data = self.pytesseract.image_to_data(
                            processed,
                            output_type=self.pytesseract.Output.DICT,
                            config=f'--oem 3 --psm {psm}'
                        )
                        
                        for i, text in enumerate(data['text']):
                            conf = int(data['conf'][i])
                            if conf > 15 and text.strip() and len(text.strip()) > 1:
                                all_texts.append(text.strip())
                                confidences.append(conf)
                    except:
                        continue
            except:
                continue
        
        if all_texts:
            result['text'] = ' '.join(set(all_texts))
            result['confidence'] = np.mean(confidences) / 100.0 if confidences else 0.0
        
        return result
    
    def _extract_text_easyocr(self, image: np.ndarray) -> Dict:
        """Extract text using EasyOCR"""
        result = {'text': '', 'confidence': 0.0}
        
        if not self.easyocr_available:
            return result
        
        try:
            # EasyOCR works better with RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Run OCR
            results = self.easyocr_reader.readtext(rgb_image)
            
            texts = []
            confidences = []
            
            for (bbox, text, conf) in results:
                if conf > 0.1 and text.strip():
                    texts.append(text.strip())
                    confidences.append(conf)
            
            if texts:
                result['text'] = ' '.join(texts)
                result['confidence'] = np.mean(confidences) if confidences else 0.0
                
        except Exception as e:
            print(f"EasyOCR error: {e}")
        
        return result
    
    def _extract_text_pil_preprocessing(self, image_path: str) -> Dict:
        """Extract text using PIL-based preprocessing"""
        result = {'text': '', 'confidence': 0.0}
        
        if not self.tesseract_available:
            return result
        
        try:
            # Load with PIL
            pil_image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Enhance
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(2.0)
            
            enhancer = ImageEnhance.Sharpness(pil_image)
            pil_image = enhancer.enhance(2.0)
            
            # Convert to grayscale
            gray = pil_image.convert('L')
            
            # Try multiple threshold values
            texts = []
            confidences = []
            
            for threshold in [100, 127, 150, 180]:
                try:
                    binary = gray.point(lambda x: 255 if x > threshold else 0)
                    
                    data = self.pytesseract.image_to_data(
                        binary,
                        output_type=self.pytesseract.Output.DICT,
                        config='--oem 3 --psm 6'
                    )
                    
                    for i, text in enumerate(data['text']):
                        conf = int(data['conf'][i])
                        if conf > 15 and text.strip() and len(text.strip()) > 1:
                            texts.append(text.strip())
                            confidences.append(conf)
                except:
                    continue
            
            if texts:
                result['text'] = ' '.join(set(texts))
                result['confidence'] = np.mean(confidences) / 100.0 if confidences else 0.0
                
        except Exception as e:
            print(f"PIL preprocessing error: {e}")
        
        return result
    
    def _preprocess_invert(self, image: np.ndarray) -> np.ndarray:
        """Invert image colors for better OCR on dark backgrounds"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        inverted = cv2.bitwise_not(gray)
        _, binary = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    
    def _preprocess_edge_enhance(self, image: np.ndarray) -> np.ndarray:
        """Enhance edges for better text detection"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Resize for better OCR
        height, width = gray.shape
        if max(height, width) < 800:
            scale = 800 / max(height, width)
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # Apply Laplacian for edge enhancement
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        enhanced = cv2.convertScaleAbs(laplacian)
        
        # Combine with original
        combined = cv2.addWeighted(gray, 0.7, enhanced, 0.3, 0)
        
        _, binary = cv2.threshold(combined, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def _extract_text(self, image: np.ndarray) -> Dict:
        """
        Extract text from image using multiple preprocessing techniques
        """
        result = {
            'text': '',
            'cleaned_text': '',
            'confidence': 0.0
        }
        
        if not self.tesseract_available:
            return result
        
        # Try multiple preprocessing methods and combine results
        all_texts = []
        confidences = []
        
        preprocessing_methods = [
            self._preprocess_default,
            self._preprocess_adaptive,
            self._preprocess_sharpen,
            self._preprocess_denoise,
            self._preprocess_resize_and_enhance,
            self._preprocess_morphological,
        ]
        
        # Try multiple PSM modes for different image types
        psm_modes = [6, 3, 11, 4]  # 6=uniform block, 3=auto, 11=sparse text, 4=single column
        
        for preprocess_func in preprocessing_methods:
            try:
                processed = preprocess_func(image)
                
                for psm in psm_modes:
                    try:
                        # Get detailed OCR data
                        data = self.pytesseract.image_to_data(
                            processed, 
                            output_type=self.pytesseract.Output.DICT,
                            config=f'--oem 3 --psm {psm}'
                        )
                        
                        # Extract text and confidence
                        texts = []
                        conf_values = []
                        
                        for i, text in enumerate(data['text']):
                            conf = int(data['conf'][i])
                            if conf > 20 and text.strip() and len(text.strip()) > 1:  # Lower threshold, filter single chars
                                texts.append(text)
                                conf_values.append(conf)
                        
                        if texts:
                            all_texts.extend(texts)
                            confidences.extend(conf_values)
                    except:
                        continue
                    
            except Exception as e:
                continue
        
        # Combine and deduplicate texts
        if all_texts:
            result['text'] = ' '.join(all_texts)
            result['cleaned_text'] = self._clean_extracted_text(' '.join(set(all_texts)))
            result['confidence'] = np.mean(confidences) / 100.0 if confidences else 0.0
        
        return result
    
    def _preprocess_default(self, image: np.ndarray) -> np.ndarray:
        """Basic preprocessing: grayscale + threshold"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    
    def _preprocess_adaptive(self, image: np.ndarray) -> np.ndarray:
        """Adaptive threshold preprocessing"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        return adaptive
    
    def _preprocess_sharpen(self, image: np.ndarray) -> np.ndarray:
        """Sharpen image before OCR"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Sharpen kernel
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        sharpened = cv2.filter2D(gray, -1, kernel)
        
        _, binary = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    
    def _preprocess_denoise(self, image: np.ndarray) -> np.ndarray:
        """Denoise image before OCR"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    
    def _preprocess_resize_and_enhance(self, image: np.ndarray) -> np.ndarray:
        """Resize small images and enhance for better OCR"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Resize if image is too small
        height, width = gray.shape
        if width < 500 or height < 500:
            scale = max(500 / width, 500 / height)
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    
    def _preprocess_morphological(self, image: np.ndarray) -> np.ndarray:
        """Apply morphological operations for better text detection"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Resize for better OCR
        height, width = gray.shape
        if width < 600:
            scale = 600 / width
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # Apply bilateral filter to reduce noise while keeping edges
        filtered = cv2.bilateralFilter(gray, 11, 17, 17)
        
        # Apply threshold
        _, binary = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Apply morphological closing to connect text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return closed
    
    def _clean_extracted_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Remove common OCR artifacts
        text = re.sub(r'[|\\\/\[\]{}]', '', text)
        
        # Normalize common medicine-related patterns
        text = re.sub(r'(\d+)\s*(mg|ml|mcg|g|l|iu)', r'\1\2', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def _extract_medicine_info(self, text: str) -> Dict:
        """Extract structured medicine information from text"""
        info = {
            'possible_names': [],
            'dosage': None,
            'form': None,
            'manufacturer': None,
            'expiry': None,
            'batch_number': None,
            'ingredients': [],
            'warnings_found': False,
        }
        
        text_lower = text.lower()
        
        # Extract dosage (e.g., 500mg, 10ml)
        dosage_pattern = r'(\d+(?:\.\d+)?)\s*(mg|ml|mcg|g|iu|units?)'
        dosages = re.findall(dosage_pattern, text_lower)
        if dosages:
            info['dosage'] = f"{dosages[0][0]}{dosages[0][1]}"
        
        # Detect form
        form_keywords = {
            'tablet': ['tablet', 'tablets', 'tab', 'tabs'],
            'capsule': ['capsule', 'capsules', 'cap', 'caps'],
            'syrup': ['syrup', 'suspension', 'liquid', 'solution'],
            'cream': ['cream', 'lotion'],
            'ointment': ['ointment'],
            'gel': ['gel'],
            'drops': ['drops', 'drop'],
            'injection': ['injection', 'inj', 'injectable', 'vial'],
            'inhaler': ['inhaler', 'inhalation'],
            'spray': ['spray', 'nasal'],
            'powder': ['powder', 'sachet'],
        }
        
        for form, keywords in form_keywords.items():
            if any(kw in text_lower for kw in keywords):
                info['form'] = form
                break
        
        # Extract expiry date
        expiry_patterns = [
            r'exp(?:iry)?[:\s]*(\d{2}[\/\-]\d{2,4})',
            r'exp(?:iry)?[:\s]*([a-z]{3}\s*\d{4})',
            r'best\s*before[:\s]*(\d{2}[\/\-]\d{2,4})',
        ]
        for pattern in expiry_patterns:
            match = re.search(pattern, text_lower)
            if match:
                info['expiry'] = match.group(1)
                break
        
        # Extract batch/lot number
        batch_patterns = [
            r'batch\s*(?:no\.?)?[:\s]*([a-z0-9]+)',
            r'lot\s*(?:no\.?)?[:\s]*([a-z0-9]+)',
            r'b\.?\s*no\.?[:\s]*([a-z0-9]+)',
        ]
        for pattern in batch_patterns:
            match = re.search(pattern, text_lower)
            if match:
                info['batch_number'] = match.group(1).upper()
                break
        
        # Check for warnings
        warning_keywords = ['warning', 'caution', 'do not', 'keep away', 'consult', 'prescription']
        info['warnings_found'] = any(kw in text_lower for kw in warning_keywords)
        
        # Extract potential medicine names (words that might be medicine names)
        # Look for capitalized words or words before dosage
        words = text.split()
        potential_names = []
        for i, word in enumerate(words):
            # Check if it's a capitalized word (potential brand name)
            if word[0].isupper() and len(word) > 2:
                # Exclude common non-name words
                exclude_words = {'The', 'For', 'And', 'With', 'Contains', 'Store', 'Keep', 'Take', 'Use'}
                if word not in exclude_words:
                    potential_names.append(word)
        
        info['possible_names'] = list(set(potential_names))[:5]  # Limit to top 5
        
        return info
    
    def _analyze_visual_features(self, image: np.ndarray) -> Dict:
        """Analyze visual features of the medicine image"""
        features = {
            'dominant_colors': [],
            'brightness': 0,
            'contrast': 0,
            'edges_detected': False,
            'circular_objects': 0,
            'rectangular_regions': 0,
        }
        
        # Convert to HSV for color analysis
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Analyze dominant colors
        features['dominant_colors'] = self._get_dominant_colors(hsv)
        
        # Calculate brightness and contrast
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        features['brightness'] = float(np.mean(gray))
        features['contrast'] = float(np.std(gray))
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        features['edges_detected'] = bool(np.sum(edges > 0) > (edges.size * 0.01))
        
        # Detect circular objects (tablets, capsules)
        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT, 1, 20,
            param1=50, param2=30, minRadius=10, maxRadius=200
        )
        features['circular_objects'] = int(len(circles[0])) if circles is not None else 0
        
        # Detect rectangular regions (packaging, labels)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rect_count = 0
        for contour in contours:
            approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
            if len(approx) == 4:
                rect_count += 1
        features['rectangular_regions'] = rect_count
        
        return features
    
    def _get_dominant_colors(self, hsv_image: np.ndarray) -> List[str]:
        """Identify dominant colors in the image"""
        dominant = []
        
        for color_name, (lower, upper) in self.color_names.items():
            lower = np.array(lower)
            upper = np.array(upper)
            
            mask = cv2.inRange(hsv_image, lower, upper)
            percentage = (np.sum(mask > 0) / mask.size) * 100
            
            if percentage > 5:  # At least 5% of image
                dominant.append({
                    'color': color_name,
                    'percentage': round(percentage, 2)
                })
        
        # Sort by percentage
        dominant.sort(key=lambda x: x['percentage'], reverse=True)
        return dominant[:3]  # Return top 3 colors
    
    def _detect_medicine_form(self, image: np.ndarray, text: str) -> str:
        """Detect medicine form based on visual features and text"""
        text_lower = text.lower()
        
        # First check text-based detection
        if 'tablet' in text_lower or 'tab' in text_lower:
            return 'tablet'
        elif 'capsule' in text_lower or 'cap' in text_lower:
            return 'capsule'
        elif 'syrup' in text_lower or 'suspension' in text_lower:
            return 'syrup'
        elif 'cream' in text_lower or 'lotion' in text_lower:
            return 'cream'
        elif 'ointment' in text_lower:
            return 'ointment'
        elif 'gel' in text_lower:
            return 'gel'
        elif 'injection' in text_lower or 'vial' in text_lower:
            return 'injection'
        elif 'drop' in text_lower:
            return 'drops'
        elif 'inhaler' in text_lower:
            return 'inhaler'
        elif 'spray' in text_lower:
            return 'spray'
        elif 'powder' in text_lower or 'sachet' in text_lower:
            return 'powder'
        
        # Visual-based detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Check for circular shapes (tablets)
        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT, 1, 20,
            param1=50, param2=30, minRadius=10, maxRadius=100
        )
        
        if circles is not None and len(circles[0]) > 0:
            # Multiple small circles might indicate tablets
            return 'tablet'
        
        # Check aspect ratio for bottles (syrups)
        h, w = image.shape[:2]
        aspect_ratio = h / w if w > 0 else 1
        
        if aspect_ratio > 2:  # Tall and narrow - likely bottle
            return 'syrup'
        
        return 'unknown'
    
    def preprocess_for_display(self, image_path: str) -> Optional[str]:
        """
        Create an enhanced version of the image for display
        Returns path to the enhanced image
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                return None
            
            # Enhance image
            # 1. Adjust brightness and contrast
            alpha = 1.2  # Contrast
            beta = 10    # Brightness
            enhanced = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
            
            # 2. Denoise
            enhanced = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7, 21)
            
            # Save to temp file
            temp_dir = tempfile.gettempdir()
            filename = os.path.basename(image_path)
            enhanced_path = os.path.join(temp_dir, f"enhanced_{filename}")
            cv2.imwrite(enhanced_path, enhanced)
            
            return enhanced_path
            
        except Exception as e:
            print(f"Error preprocessing image: {e}")
            return None
    def _validate_medicine_image(self, analysis_results: Dict) -> Dict:
        """
        Validate if the analyzed image is actually a medicine image
        
        Args:
            analysis_results: Results from the image analysis
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'is_valid': False,
            'confidence_score': 0.0,
            'reason': '',
            'suggestions': []
        }
        
        score = 0.0
        reasons = []
        
        # Get extracted text
        extracted_text = analysis_results.get('cleaned_text', '').lower()
        raw_text = analysis_results.get('extracted_text', '').lower()
        combined_text = f"{extracted_text} {raw_text}"
        
        # Get detected medicine info
        detected_info = analysis_results.get('detected_medicine_info', {})
        visual_analysis = analysis_results.get('visual_analysis', {})
        
        # Check 1: Strong medicine keywords in text (high weight)
        strong_indicators_found = []
        for keyword in self.strong_medicine_indicators:
            if keyword.lower() in combined_text:
                strong_indicators_found.append(keyword)
        
        if len(strong_indicators_found) >= 3:
            score += 0.5
            reasons.append(f"Found medicine-related keywords: {', '.join(strong_indicators_found[:5])}")
        elif len(strong_indicators_found) >= 1:
            score += 0.25
            reasons.append(f"Found some medicine keywords: {', '.join(strong_indicators_found[:3])}")
        
        # Check 2: Non-medicine keywords (negative weight)
        non_medicine_found = []
        for keyword in self.non_medicine_indicators:
            if keyword.lower() in combined_text:
                non_medicine_found.append(keyword)
        
        if len(non_medicine_found) >= 2:
            score -= 0.3
            reasons.append(f"Found non-medicine content indicators: {', '.join(non_medicine_found[:3])}")
        
        # Check 3: Detected dosage information
        if detected_info.get('dosage'):
            score += 0.2
            reasons.append(f"Detected dosage: {detected_info['dosage']}")
        
        # Check 4: Detected medicine form
        if detected_info.get('form'):
            score += 0.15
            reasons.append(f"Detected form: {detected_info['form']}")
        
        # Check 5: Batch/expiry information
        if detected_info.get('expiry') or detected_info.get('batch_number'):
            score += 0.15
            reasons.append("Found batch/expiry information")
        
        # Check 6: Warnings found
        if detected_info.get('warnings_found'):
            score += 0.1
            reasons.append("Medical warnings detected")
        
        # Check 7: Visual features analysis
        detected_form = visual_analysis.get('detected_form', 'unknown')
        if detected_form != 'unknown':
            score += 0.1
            reasons.append(f"Visual form detected: {detected_form}")
        
        # Check 8: Circular objects (tablets/capsules)
        circular_objects = visual_analysis.get('circular_objects', 0)
        if circular_objects > 0:
            score += 0.1
            reasons.append(f"Detected {circular_objects} circular objects (possible tablets)")
        
        # Check 9: Possible medicine names detected
        possible_names = detected_info.get('possible_names', [])
        if possible_names:
            score += 0.1
            reasons.append(f"Possible medicine names: {', '.join(possible_names[:3])}")
        
        # Check 10: Detected brand from patterns
        if detected_info.get('detected_brand'):
            score += 0.25
            reasons.append(f"Detected brand: {detected_info['detected_brand']}")
        
        # Check 11: OCR confidence - very low might indicate non-text image
        ocr_confidence = analysis_results.get('ocr_confidence', 0)
        if ocr_confidence < 0.1 and len(combined_text.strip()) < 10:
            score -= 0.1
            reasons.append("Very low text content detected")
        
        # Check 12: Color analysis for medicine packaging
        dominant_colors = visual_analysis.get('dominant_colors', [])
        medicine_packaging_colors = ['white', 'blue', 'green', 'red', 'yellow']
        for color_info in dominant_colors:
            if color_info.get('color') in medicine_packaging_colors and color_info.get('percentage', 0) > 10:
                score += 0.05
        
        # Normalize score to 0-1 range
        score = max(0.0, min(1.0, score))
        
        # Determine validation result
        validation['confidence_score'] = round(score, 2)
        
        if score >= self.min_medicine_confidence:
            validation['is_valid'] = True
            validation['reason'] = "Image appears to contain medicine-related content. " + " | ".join(reasons[:3])
        else:
            validation['is_valid'] = False
            if not combined_text.strip():
                validation['reason'] = "No readable text found in the image. This doesn't appear to be a medicine image."
                validation['suggestions'] = [
                    "Please upload a clear image of medicine packaging, tablet strip, or medicine bottle",
                    "Ensure the medicine label or packaging text is clearly visible",
                    "Try taking the photo in good lighting conditions",
                    "Avoid blurry or low-quality images"
                ]
            elif non_medicine_found:
                validation['reason'] = f"The image appears to contain non-medicine content ({', '.join(non_medicine_found[:2])}). Please upload a valid medicine image."
                validation['suggestions'] = [
                    "Please upload an image of actual medicine packaging, tablets, or medicine bottles",
                    "The system is designed to identify pharmaceutical products only"
                ]
            else:
                validation['reason'] = "Unable to detect medicine-related content in the image."
                validation['suggestions'] = [
                    "Upload a clear photo of the medicine packaging showing the name and dosage",
                    "Ensure the medicine label is clearly visible and readable",
                    "Include the full medicine strip or bottle label in the frame",
                    "Acceptable images: medicine boxes, tablet strips, syrup bottles, cream tubes, etc."
                ]
        
        return validation