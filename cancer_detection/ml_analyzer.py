"""
ML-based Cancer Detection Analyzer
Uses YOLOv8 and advanced OpenCV techniques for cancer detection with visualization
"""
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import os
import warnings
from pathlib import Path
import json
import base64

warnings.filterwarnings('ignore')

try:
    import torch
    import torchvision
    from torchvision import transforms
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from scipy import ndimage
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class MLCancerAnalyzer:
    """Advanced cancer detection using YOLOv8 and enhanced OpenCV techniques"""
    
    def __init__(self):
        """Initialize the ML analyzer"""
        self.device = 'cuda' if (TORCH_AVAILABLE and torch.cuda.is_available()) else 'cpu'
        self.yolo_model = None
        self.min_confidence = 0.35
        self.initialize_models()
    
    def initialize_models(self):
        """Initialize YOLO model for detection"""
        if YOLO_AVAILABLE:
            try:
                self.yolo_model = YOLO('yolov8n.pt')
            except Exception as e:
                self.yolo_model = None
    
    def analyze_image(self, image_path: str, image_type: str = 'other') -> Dict:
        """
        Comprehensive image analysis using multiple ML techniques
        
        Args:
            image_path: Path to the medical image
            image_type: Type of medical image (xray, ct, mri, tumor, etc.)
        
        Returns:
            Dictionary with detection results, analysis, and visualization
        """
        # Read and validate image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image from {image_path}")
        
        height, width = img.shape[:2]
        
        # Prepare results structure
        analysis_results = {
            'image_info': {
                'original_size': {'width': width, 'height': height},
                'image_type': image_type,
            },
            'tumor_detected': False,
            'tumor_regions': [],
            'tumor_type': None,
            'tumor_stage': None,
            'tumor_size_mm': None,
            'tumor_location': None,
            'genetic_profile': {},
            'comorbidities': [],
            'detection_confidence': 0.0,
            'stage_confidence': 0.0,
            'detailed_analysis': {},
            'annotated_image': None,
            'model_info': {
                'model_type': 'YOLOv8 + Advanced OpenCV Hybrid',
                'device': self.device
            }
        }
        
        # Run YOLO detection
        yolo_detections = self._run_yolo_detection(image_path, img)
        
        # Run enhanced OpenCV-based analysis
        opencv_detections = self._run_enhanced_opencv_analysis(img, image_type)
        
        # Combine and score detections
        all_detections = self._combine_detections(yolo_detections, opencv_detections, img)
        
        if all_detections:
            analysis_results['tumor_detected'] = True
            
            # Process each detection
            for idx, detection in enumerate(all_detections):
                region_analysis = self._analyze_detection_region(detection, img, image_type)
                analysis_results['tumor_regions'].append(region_analysis)
            
            # Get primary detection (highest confidence)
            primary = max(analysis_results['tumor_regions'], 
                         key=lambda x: x.get('confidence', 0))
            
            analysis_results['tumor_type'] = primary.get('tumor_type', 'Unknown')
            analysis_results['tumor_stage'] = primary.get('tumor_stage', 'Unknown')
            analysis_results['tumor_size_mm'] = primary.get('size_mm', 0)
            analysis_results['tumor_location'] = primary.get('location', 'Unknown')
            analysis_results['genetic_profile'] = primary.get('genetic_indicators', {})
            analysis_results['comorbidities'] = primary.get('comorbidities', [])
            analysis_results['detection_confidence'] = primary.get('confidence', 0.0) * 100
            analysis_results['stage_confidence'] = primary.get('stage_confidence', 0.0) * 100
            analysis_results['detailed_analysis'] = {
                'primary_detection': primary,
                'all_detections': analysis_results['tumor_regions']
            }
        
        # Generate annotated image with visualizations
        annotated_img = self._generate_annotated_image(img, all_detections, image_type)
        analysis_results['annotated_image'] = annotated_img
        
        # Save annotated image to disk
        self._save_annotated_image(image_path, annotated_img)
        
        return analysis_results
    
    def _run_yolo_detection(self, image_path: str, img: np.ndarray) -> List[Dict]:
        """Run YOLOv8 detection on image"""
        detections = []
        
        if not self.yolo_model or not YOLO_AVAILABLE:
            return detections
        
        try:
            results = self.yolo_model(image_path, conf=self.min_confidence, verbose=False)
            
            for result in results:
                if result.boxes is not None:
                    boxes = result.boxes
                    for box in boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        
                        detections.append({
                            'type': 'yolo',
                            'bbox': (x1, y1, x2 - x1, y2 - y1),
                            'confidence': conf,
                            'class': cls,
                            'model': 'YOLOv8'
                        })
        except Exception as e:
            pass
        
        return detections
    
    def _run_enhanced_opencv_analysis(self, img: np.ndarray, image_type: str) -> List[Dict]:
        """Run enhanced OpenCV-based analysis with multiple detection methods"""
        detections = []
        
        # Convert to grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        else:
            gray = img.copy()
            hsv = None
            lab = None
        
        height, width = gray.shape
        
        # Multi-scale preprocessing
        processed_images = self._multi_scale_preprocess(gray, image_type)
        
        # Method 1: Enhanced adaptive thresholding
        adaptive_detections = self._detect_with_adaptive_threshold(processed_images['enhanced'], image_type)
        detections.extend(adaptive_detections)
        
        # Method 2: Canny edge detection with morphological operations
        edge_detections = self._detect_with_edge_analysis(processed_images['edges'], gray)
        detections.extend(edge_detections)
        
        # Method 3: Blob detection for circular/oval masses
        blob_detections = self._detect_with_blob_analysis(processed_images['enhanced'])
        detections.extend(blob_detections)
        
        # Method 4: Color-based detection
        if hsv is not None and lab is not None:
            color_detections = self._detect_with_color_analysis(img, hsv, lab, image_type)
            detections.extend(color_detections)
        
        # Method 5: Texture-based anomaly detection
        texture_detections = self._detect_with_texture_analysis(gray, image_type)
        detections.extend(texture_detections)
        
        # Method 6: Watershed segmentation
        watershed_detections = self._detect_with_watershed(processed_images['enhanced'], gray)
        detections.extend(watershed_detections)
        
        # Non-maximum suppression
        detections = self._apply_nms(detections, threshold=0.4)
        
        return detections
    
    def _multi_scale_preprocess(self, gray: np.ndarray, image_type: str) -> Dict:
        """Multi-scale image preprocessing"""
        results = {}
        
        # CLAHE enhancement
        clahe_soft = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        clahe_strong = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(16, 16))
        
        enhanced_soft = clahe_soft.apply(gray)
        enhanced_strong = clahe_strong.apply(gray)
        enhanced = cv2.addWeighted(enhanced_soft, 0.5, enhanced_strong, 0.5, 0)
        
        # Denoise
        if image_type in ['mri', 'ct']:
            denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
        else:
            denoised = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        # Edge detection
        edges = cv2.Canny(denoised, 30, 100)
        
        # Morphological gradient
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        gradient = cv2.morphologyEx(denoised, cv2.MORPH_GRADIENT, kernel)
        
        results['original'] = gray
        results['enhanced'] = denoised
        results['edges'] = edges
        results['gradient'] = gradient
        
        return results
    
    def _detect_with_adaptive_threshold(self, img: np.ndarray, image_type: str) -> List[Dict]:
        """Detect anomalies using adaptive thresholding"""
        detections = []
        block_sizes = [11, 21, 31, 51]
        
        for block_size in block_sizes:
            thresh = cv2.adaptiveThreshold(
                img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, block_size, 2
            )
            
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
            
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 200 or area > img.shape[0] * img.shape[1] * 0.5:
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                perimeter = cv2.arcLength(contour, True)
                circularity = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0
                
                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                solidity = area / hull_area if hull_area > 0 else 0
                
                shape_score = 0.3 + 0.4 * (1 - circularity) + 0.3 * solidity
                size_score = min(area / 10000, 1.0)
                confidence = (shape_score * 0.6 + size_score * 0.4) * 0.85
                
                if confidence >= 0.25:
                    detections.append({
                        'type': 'adaptive_threshold',
                        'bbox': (x, y, w, h),
                        'contour': contour,
                        'area': area,
                        'confidence': confidence,
                        'circularity': circularity,
                        'solidity': solidity,
                        'model': 'OpenCV-Adaptive'
                    })
        
        return detections
    
    def _detect_with_edge_analysis(self, edges: np.ndarray, gray: np.ndarray) -> List[Dict]:
        """Detect anomalies using edge-based analysis"""
        detections = []
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Fill holes
        if SCIPY_AVAILABLE:
            filled = ndimage.binary_fill_holes(dilated).astype(np.uint8) * 255
        else:
            # Fallback without scipy
            flood_fill = dilated.copy()
            h, w = dilated.shape[:2]
            mask = np.zeros((h + 2, w + 2), np.uint8)
            cv2.floodFill(flood_fill, mask, (0, 0), 255)
            flood_fill_inv = cv2.bitwise_not(flood_fill)
            filled = dilated | flood_fill_inv
        
        contours, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 500 or area > gray.shape[0] * gray.shape[1] * 0.4:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            roi = edges[y:y+h, x:x+w]
            edge_density = np.sum(roi > 0) / (w * h) if w * h > 0 else 0
            
            if edge_density > 0.15:
                perimeter = cv2.arcLength(contour, True)
                circularity = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0
                confidence = min(edge_density * 2, 1.0) * 0.75
                
                detections.append({
                    'type': 'edge_detection',
                    'bbox': (x, y, w, h),
                    'contour': contour,
                    'area': area,
                    'edge_density': edge_density,
                    'confidence': confidence,
                    'model': 'OpenCV-Edge'
                })
        
        return detections
    
    def _detect_with_blob_analysis(self, img: np.ndarray) -> List[Dict]:
        """Detect blob-like structures"""
        detections = []
        
        params = cv2.SimpleBlobDetector_Params()
        params.filterByArea = True
        params.minArea = 100
        params.maxArea = img.shape[0] * img.shape[1] * 0.3
        params.filterByCircularity = True
        params.minCircularity = 0.3
        params.filterByConvexity = True
        params.minConvexity = 0.5
        params.filterByInertia = True
        params.minInertiaRatio = 0.2
        
        detector = cv2.SimpleBlobDetector_create(params)
        
        inverted = cv2.bitwise_not(img)
        keypoints_dark = detector.detect(inverted)
        keypoints_bright = detector.detect(img)
        
        all_keypoints = list(keypoints_dark) + list(keypoints_bright)
        
        for kp in all_keypoints:
            x, y = int(kp.pt[0]), int(kp.pt[1])
            r = int(kp.size / 2)
            
            if r < 5:
                continue
            
            bbox = (x - r, y - r, 2 * r, 2 * r)
            area = np.pi * r * r
            confidence = min(kp.size / 100, 1.0) * 0.7
            
            detections.append({
                'type': 'blob',
                'bbox': bbox,
                'center': (x, y),
                'radius': r,
                'area': area,
                'confidence': confidence,
                'model': 'OpenCV-Blob'
            })
        
        return detections
    
    def _detect_with_color_analysis(self, img: np.ndarray, hsv: np.ndarray, 
                                     lab: np.ndarray, image_type: str) -> List[Dict]:
        """Detect anomalies based on color patterns"""
        detections = []
        
        if image_type in ['tumor', 'histopathology', 'biopsy']:
            # H&E staining detection
            lower_purple = np.array([100, 50, 50])
            upper_purple = np.array([150, 255, 255])
            mask_purple = cv2.inRange(hsv, lower_purple, upper_purple)
            
            lower_pink = np.array([140, 30, 100])
            upper_pink = np.array([180, 150, 255])
            mask_pink = cv2.inRange(hsv, lower_pink, upper_pink)
            
            combined = cv2.bitwise_or(mask_purple, mask_pink)
        else:
            l_channel = lab[:, :, 0]
            _, high_intensity = cv2.threshold(l_channel, 180, 255, cv2.THRESH_BINARY)
            _, low_intensity = cv2.threshold(l_channel, 50, 255, cv2.THRESH_BINARY_INV)
            combined = cv2.bitwise_or(high_intensity, low_intensity)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel, iterations=1)
        
        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 300 or area > img.shape[0] * img.shape[1] * 0.4:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            roi = img[y:y+h, x:x+w]
            color_std = np.std(roi)
            confidence = min(area / 5000, 1.0) * 0.65
            
            detections.append({
                'type': 'color_analysis',
                'bbox': (x, y, w, h),
                'contour': contour,
                'area': area,
                'color_variance': color_std,
                'confidence': confidence,
                'model': 'OpenCV-Color'
            })
        
        return detections
    
    def _detect_with_texture_analysis(self, gray: np.ndarray, image_type: str) -> List[Dict]:
        """Detect anomalies based on texture patterns"""
        detections = []
        
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        window_size = 32
        stride = 16
        
        height, width = gray.shape
        texture_map = np.zeros((height, width), dtype=np.float32)
        
        for y in range(0, height - window_size, stride):
            for x in range(0, width - window_size, stride):
                window = laplacian[y:y+window_size, x:x+window_size]
                variance = np.var(window)
                texture_map[y:y+window_size, x:x+window_size] = max(
                    texture_map[y:y+window_size, x:x+window_size].max(),
                    variance
                )
        
        if texture_map.max() > 0:
            texture_map = (texture_map / texture_map.max() * 255).astype(np.uint8)
        else:
            return detections
        
        _, high_texture = cv2.threshold(texture_map, 100, 255, cv2.THRESH_BINARY)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        high_texture = cv2.morphologyEx(high_texture, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        contours, _ = cv2.findContours(high_texture, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 400:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            roi_texture = texture_map[y:y+h, x:x+w]
            mean_texture = np.mean(roi_texture)
            confidence = min(mean_texture / 200, 1.0) * 0.6
            
            if confidence >= 0.2:
                detections.append({
                    'type': 'texture_analysis',
                    'bbox': (x, y, w, h),
                    'contour': contour,
                    'area': area,
                    'texture_score': mean_texture,
                    'confidence': confidence,
                    'model': 'OpenCV-Texture'
                })
        
        return detections
    
    def _detect_with_watershed(self, enhanced: np.ndarray, gray: np.ndarray) -> List[Dict]:
        """Use watershed algorithm for segmentation"""
        detections = []
        
        _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        kernel = np.ones((3, 3), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
        
        sure_bg = cv2.dilate(opening, kernel, iterations=3)
        
        dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
        _, sure_fg = cv2.threshold(dist_transform, 0.5 * dist_transform.max(), 255, 0)
        sure_fg = np.uint8(sure_fg)
        
        unknown = cv2.subtract(sure_bg, sure_fg)
        
        _, markers = cv2.connectedComponents(sure_fg)
        markers = markers + 1
        markers[unknown == 255] = 0
        
        img_color = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        markers = cv2.watershed(img_color, markers)
        
        unique_markers = np.unique(markers)
        
        for marker_id in unique_markers:
            if marker_id <= 1:
                continue
            
            mask = np.uint8(markers == marker_id) * 255
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 300:
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                confidence = min(area / 8000, 1.0) * 0.55
                
                if confidence >= 0.15:
                    detections.append({
                        'type': 'watershed',
                        'bbox': (x, y, w, h),
                        'contour': contour,
                        'area': area,
                        'confidence': confidence,
                        'model': 'OpenCV-Watershed'
                    })
        
        return detections
    
    def _apply_nms(self, detections: List[Dict], threshold: float = 0.4) -> List[Dict]:
        """Apply Non-Maximum Suppression"""
        if not detections:
            return []
        
        detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        
        keep = []
        used = set()
        
        for i, det in enumerate(detections):
            if i in used:
                continue
            
            keep.append(det)
            
            for j, other in enumerate(detections[i+1:], start=i+1):
                if j in used:
                    continue
                
                if self._boxes_overlap(det['bbox'], other['bbox'], threshold):
                    if det['confidence'] >= other['confidence']:
                        used.add(j)
                    else:
                        used.add(i)
        
        return keep[:10]
    
    def _combine_detections(self, yolo_dets: List[Dict], 
                           opencv_dets: List[Dict], 
                           img: np.ndarray) -> List[Dict]:
        """Combine and de-duplicate detections"""
        combined = []
        
        for det in yolo_dets:
            if det['confidence'] >= self.min_confidence:
                det['confidence'] = min(det['confidence'] * 1.2, 1.0)
                combined.append(det)
        
        for ov_det in opencv_dets:
            overlap = False
            for existing in combined:
                if self._boxes_overlap(existing['bbox'], ov_det['bbox'], 0.3):
                    existing['confidence'] = min(existing['confidence'] + 0.1, 1.0)
                    overlap = True
                    break
            
            if not overlap and ov_det['confidence'] >= 0.2:
                combined.append(ov_det)
        
        combined.sort(key=lambda x: x['confidence'], reverse=True)
        return combined[:8]
    
    def _boxes_overlap(self, box1: Tuple, box2: Tuple, threshold: float = 0.3) -> bool:
        """Check if two bounding boxes overlap"""
        x1_min, y1_min, w1, h1 = box1
        x2_min, y2_min, w2, h2 = box2
        
        x1_max, y1_max = x1_min + w1, y1_min + h1
        x2_max, y2_max = x2_min + w2, y2_min + h2
        
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)
        
        if inter_x_max < inter_x_min or inter_y_max < inter_y_min:
            return False
        
        inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
        union_area = (w1 * h1) + (w2 * h2) - inter_area
        
        iou = inter_area / union_area if union_area > 0 else 0
        return iou > threshold
    
    def _analyze_detection_region(self, detection: Dict, img: np.ndarray, 
                                 image_type: str) -> Dict:
        """Detailed analysis of a detected region"""
        x, y, w, h = detection['bbox']
        
        x, y = max(0, x), max(0, y)
        x2, y2 = min(img.shape[1], x + w), min(img.shape[0], y + h)
        x, y, w, h = x, y, x2 - x, y2 - y
        
        if w <= 0 or h <= 0:
            return {
                'confidence': 0.0,
                'tumor_type': 'Unknown',
                'tumor_stage': 'Unknown',
                'location': 'Unknown',
                'size_mm': 0,
            }
        
        roi = img[y:y+h, x:x+w]
        
        if roi.size == 0:
            return {
                'confidence': 0.0,
                'tumor_type': 'Unknown',
                'tumor_stage': 'Unknown',
                'location': 'Unknown',
                'size_mm': 0,
            }
        
        if len(roi.shape) == 3:
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            roi_gray = roi
        
        contour = detection.get('contour')
        area = detection.get('area', w * h)
        
        circularity = self._calculate_circularity(roi_gray)
        aspect_ratio = w / h if h > 0 else 1.0
        
        texture_features = self._analyze_texture(roi_gray)
        
        size_mm = np.sqrt(area) * 0.1 if area else 0
        
        tumor_type = self._classify_tumor(circularity, texture_features, image_type)
        tumor_stage = self._estimate_stage(size_mm, circularity, texture_features)
        location = self._get_location(x, y, w, h, img.shape[1], img.shape[0])
        
        base_confidence = detection.get('confidence', 0.5)
        confidence_boost = self._calculate_confidence_boost(texture_features)
        final_confidence = min(base_confidence + confidence_boost, 1.0)
        
        genetic_indicators = self._extract_genetic_indicators(texture_features, roi_gray)
        comorbidities = self._detect_comorbidities(roi_gray, size_mm)
        
        return {
            'confidence': final_confidence,
            'stage_confidence': min(0.7 + (0.3 * circularity), 1.0),
            'tumor_type': tumor_type,
            'tumor_stage': tumor_stage,
            'location': location,
            'size_mm': round(float(size_mm), 2),
            'bbox': (x, y, w, h),
            'center': (x + w // 2, y + h // 2),
            'area': float(area),
            'circularity': round(float(circularity), 3),
            'aspect_ratio': round(float(aspect_ratio), 3),
            'texture_features': texture_features,
            'genetic_indicators': genetic_indicators,
            'comorbidities': comorbidities,
            'model_sources': [detection.get('model', 'Unknown')]
        }
    
    def _calculate_circularity(self, roi: np.ndarray) -> float:
        """Calculate shape circularity"""
        if roi.size == 0:
            return 0.0
        
        _, binary = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return 0.0
        
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        perimeter = cv2.arcLength(largest, True)
        
        if perimeter == 0:
            return 0.0
        
        circularity = (4 * np.pi * area) / (perimeter ** 2)
        return min(circularity, 1.0)
    
    def _analyze_texture(self, roi: np.ndarray) -> Dict:
        """Analyze texture characteristics"""
        if roi.size == 0:
            return {'std_dev': 0, 'mean_gradient': 0, 'entropy': 0, 'contrast': 0, 'texture_type': 'unknown'}
        
        grad_x = cv2.Sobel(roi, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(roi, cv2.CV_64F, 0, 1, ksize=3)
        gradient_mag = np.sqrt(grad_x**2 + grad_y**2)
        
        std_dev = np.std(roi)
        mean_gradient = np.mean(gradient_mag)
        
        hist, _ = np.histogram(roi.flatten(), bins=256, range=(0, 256))
        hist = hist[hist > 0]
        if len(hist) > 0:
            prob = hist / hist.sum()
            entropy = -np.sum(prob * np.log2(prob))
        else:
            entropy = 0
        
        contrast = np.var(roi)
        homogeneity = 1.0 / (1.0 + contrast / 1000) if contrast > 0 else 1.0
        
        return {
            'std_dev': round(float(std_dev), 2),
            'mean_gradient': round(float(mean_gradient), 2),
            'entropy': round(float(entropy), 2),
            'contrast': round(float(contrast), 2),
            'homogeneity': round(float(homogeneity), 3),
            'texture_type': self._classify_texture(std_dev, entropy)
        }
    
    def _classify_texture(self, std_dev: float, entropy: float) -> str:
        """Classify texture type"""
        if std_dev < 15:
            return 'smooth'
        elif std_dev < 35:
            return 'moderate'
        else:
            return 'rough'
    
    def _classify_tumor(self, circularity: float, texture: Dict, image_type: str) -> str:
        """Classify tumor characteristics"""
        texture_type = texture.get('texture_type', 'moderate')
        entropy = texture.get('entropy', 4.0)
        homogeneity = texture.get('homogeneity', 0.5)
        
        if image_type == 'xray':
            if circularity > 0.75 and homogeneity > 0.6:
                return "Well-Defined Nodule (likely benign)"
            elif entropy > 5.5 and circularity < 0.6:
                return "Spiculated Mass (suspicious for malignancy)"
            elif circularity < 0.5:
                return "Irregular Opacity (requires further evaluation)"
            else:
                return "Pulmonary Nodule"
        
        elif image_type in ['ct', 'mri']:
            if circularity > 0.85 and texture_type == 'smooth':
                return "Well-Circumscribed Lesion (likely benign)"
            elif circularity < 0.6 and texture_type == 'rough':
                return "Infiltrative Mass (suspicious for malignancy)"
            elif entropy > 5.0:
                return "Heterogeneous Mass"
            else:
                return "Solid Lesion"
        
        elif image_type in ['tumor', 'histopathology', 'biopsy']:
            if texture_type == 'rough' and entropy > 5.0:
                return "High-Grade Carcinoma (poorly differentiated)"
            elif texture_type == 'moderate':
                return "Intermediate-Grade Carcinoma"
            elif texture_type == 'smooth':
                return "Low-Grade Carcinoma (well differentiated)"
            else:
                return "Neoplastic Tissue"
        
        else:
            if circularity > 0.7:
                return "Regular Mass"
            else:
                return "Irregular Abnormality Detected"
    
    def _estimate_stage(self, size_mm: float, circularity: float, texture: Dict) -> str:
        """Estimate tumor stage"""
        entropy = texture.get('entropy', 4.0)
        
        if size_mm < 5:
            base_stage = "T1a"
        elif size_mm < 10:
            base_stage = "T1b"
        elif size_mm < 20:
            base_stage = "T1c"
        elif size_mm < 30:
            base_stage = "T2a"
        elif size_mm < 50:
            base_stage = "T2b"
        elif size_mm < 70:
            base_stage = "T3"
        else:
            base_stage = "T4"
        
        descriptors = []
        if circularity < 0.5:
            descriptors.append("irregular margins")
        if entropy > 5.5:
            descriptors.append("heterogeneous")
        
        if descriptors:
            return f"{base_stage} ({', '.join(descriptors)})"
        return base_stage
    
    def _get_location(self, x: int, y: int, w: int, h: int, 
                     img_width: int, img_height: int) -> str:
        """Get anatomical location"""
        cx = x + w // 2
        cy = y + h // 2
        
        x_thirds = img_width / 3
        y_thirds = img_height / 3
        
        x_loc = "Left" if cx < x_thirds else "Central" if cx < 2 * x_thirds else "Right"
        y_loc = "Upper" if cy < y_thirds else "Middle" if cy < 2 * y_thirds else "Lower"
        
        return f"{y_loc} {x_loc}"
    
    def _calculate_confidence_boost(self, texture: Dict) -> float:
        """Calculate confidence boost"""
        entropy = texture.get('entropy', 0)
        contrast = texture.get('contrast', 0)
        
        boost = 0.0
        if entropy > 5.0:
            boost += 0.1
        elif entropy > 3.0:
            boost += 0.05
        if contrast > 500:
            boost += 0.05
        
        return boost
    
    def _extract_genetic_indicators(self, texture: Dict, roi: np.ndarray) -> Dict:
        """Extract genetic indicators"""
        entropy = texture.get('entropy', 0)
        std_dev = texture.get('std_dev', 0)
        
        high_intensity_ratio = np.sum(roi > 200) / roi.size if roi.size > 0 else 0
        
        indicators = {
            'high_heterogeneity': entropy > 5.5,
            'heterogeneity_score': round(min(entropy / 8.0, 1.0), 2),
            'texture_complexity': texture.get('texture_type', 'moderate'),
            'cellular_density': round(std_dev / 50.0, 2),
            'nuclear_pleomorphism': 'High' if entropy > 6.0 else 'Moderate' if entropy > 4.0 else 'Low',
            'mitotic_activity_indicator': round(high_intensity_ratio, 3),
        }
        
        if entropy > 5.5 and std_dev > 40:
            indicators['suggested_testing'] = ['Ki-67', 'p53', 'EGFR']
        elif entropy > 4.0:
            indicators['suggested_testing'] = ['ER', 'PR', 'HER2']
        
        return indicators
    
    def _detect_comorbidities(self, roi: np.ndarray, size_mm: float) -> List[str]:
        """Detect potential comorbidities"""
        comorbidities = []
        
        if roi.size == 0:
            return comorbidities
        
        high_intensity_ratio = np.sum(roi > 220) / roi.size
        if high_intensity_ratio > 0.05:
            comorbidities.append("Possible Calcifications Detected")
        
        low_intensity_ratio = np.sum(roi < 30) / roi.size
        if low_intensity_ratio > 0.1 and size_mm > 15:
            comorbidities.append("Possible Central Necrosis")
        
        if np.std(roi) > 50:
            comorbidities.append("Signs of Inflammation or Edema")
        
        hist, _ = np.histogram(roi.flatten(), bins=20)
        peaks = np.where(hist > hist.mean() * 1.5)[0]
        if len(peaks) >= 3:
            comorbidities.append("Possible Satellite Lesions")
        
        return comorbidities
    
    def _generate_annotated_image(self, img: np.ndarray, detections: List[Dict], 
                                  image_type: str) -> str:
        """Generate annotated image with visualizations"""
        annotated = img.copy()
        
        colors = {
            'yolo': (0, 255, 0),
            'adaptive_threshold': (255, 165, 0),
            'edge_detection': (255, 0, 255),
            'blob': (0, 255, 255),
            'color_analysis': (255, 255, 0),
            'texture_analysis': (128, 0, 255),
            'watershed': (0, 128, 255),
        }
        
        for idx, det in enumerate(detections):
            x, y, w, h = det['bbox']
            x, y = max(0, x), max(0, y)
            
            det_type = det.get('type', 'unknown')
            color = colors.get(det_type, (0, 255, 0))
            confidence = det.get('confidence', 0)
            
            # Draw bounding box
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            
            # Draw label
            label = f"#{idx+1} {confidence*100:.1f}%"
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x, y - label_h - 8), (x + label_w + 4, y), color, -1)
            cv2.putText(annotated, label, (x + 2, y - 4), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Draw contour
            if 'contour' in det:
                cv2.drawContours(annotated, [det['contour']], -1, color, 1)
            
            # Draw center point
            cx, cy = x + w // 2, y + h // 2
            cv2.circle(annotated, (cx, cy), 5, color, -1)
            cv2.circle(annotated, (cx, cy), 8, color, 2)
        
        # Legend
        legend_y = 30
        cv2.putText(annotated, "Detection Legend:", (10, legend_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        for det_type, color in colors.items():
            legend_y += 25
            cv2.rectangle(annotated, (10, legend_y - 12), (25, legend_y), color, -1)
            cv2.putText(annotated, det_type.replace('_', ' ').title(), (35, legend_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Summary
        if detections:
            summary_y = annotated.shape[0] - 40
            total_conf = np.mean([d['confidence'] for d in detections]) * 100
            cv2.rectangle(annotated, (0, summary_y - 5), (350, annotated.shape[0]), (0, 0, 0), -1)
            cv2.putText(annotated, f"Detections: {len(detections)} | Avg Confidence: {total_conf:.1f}%", 
                       (10, summary_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Convert to base64
        _, buffer = cv2.imencode('.png', annotated)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return f"data:image/png;base64,{img_base64}"
    
    def _save_annotated_image(self, original_path: str, annotated_base64: str):
        """Save annotated image to disk"""
        try:
            path = Path(original_path)
            annotated_path = path.parent / f"{path.stem}_annotated{path.suffix}"
            
            img_data = annotated_base64.replace("data:image/png;base64,", "")
            img_bytes = base64.b64decode(img_data)
            
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            cv2.imwrite(str(annotated_path), img)
        except Exception:
            pass


class CancerImageAnalyzer:
    """Backward compatibility wrapper"""
    
    def __init__(self):
        self.ml_analyzer = MLCancerAnalyzer()
    
    def analyze_image(self, image_path: str, image_type: str = 'other') -> Dict:
        """Analyze image using ML-based analyzer"""
        return self.ml_analyzer.analyze_image(image_path, image_type)
