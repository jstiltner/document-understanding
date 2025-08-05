import logging
from typing import Dict, Any, List
import cv2
import numpy as np
from PIL import Image
import pytesseract
import os
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)

class DocumentQualityService:
    """Service for assessing document quality and providing improvement recommendations"""
    
    def __init__(self):
        self.min_dpi = 200
        self.min_clarity_score = 0.6
        self.min_text_density = 0.3
    
    def assess_document_quality(self, file_path: str) -> Dict[str, Any]:
        """
        Assess the quality of a document and provide recommendations
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary containing quality metrics and recommendations
        """
        try:
            # Convert PDF to images if necessary
            if file_path.lower().endswith('.pdf'):
                images = convert_from_path(file_path, dpi=200, first_page=1, last_page=1)
                if not images:
                    raise ValueError("Could not convert PDF to image")
                image = images[0]
                # Save temporary image for analysis
                temp_path = file_path.replace('.pdf', '_temp.png')
                image.save(temp_path)
                image_path = temp_path
            else:
                image_path = file_path
                image = Image.open(file_path)
            
            # Assess image quality
            quality_metrics = self._assess_image_quality(image_path, image)
            
            # Assess text quality
            text_metrics = self._assess_text_quality(image_path)
            
            # Calculate overall quality score
            overall_score = self._calculate_overall_score(quality_metrics, text_metrics)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(quality_metrics, text_metrics, overall_score)
            
            # Clean up temporary file
            if file_path.lower().endswith('.pdf') and os.path.exists(temp_path):
                os.remove(temp_path)
            
            return {
                "image_dpi": quality_metrics.get("dpi", 0),
                "image_clarity_score": quality_metrics.get("clarity_score", 0.0),
                "text_density_score": text_metrics.get("text_density", 0.0),
                "overall_quality_score": overall_score,
                "quality_issues": self._identify_issues(quality_metrics, text_metrics),
                "recommendations": recommendations,
                "detailed_metrics": {
                    "image_metrics": quality_metrics,
                    "text_metrics": text_metrics
                }
            }
            
        except Exception as e:
            logger.error(f"Error assessing document quality: {str(e)}")
            return {
                "image_dpi": 0,
                "image_clarity_score": 0.0,
                "text_density_score": 0.0,
                "overall_quality_score": 0.0,
                "quality_issues": [f"Quality assessment failed: {str(e)}"],
                "recommendations": ["Manual quality review required"],
                "detailed_metrics": {}
            }
    
    def _assess_image_quality(self, image_path: str, pil_image: Image.Image) -> Dict[str, Any]:
        """Assess image-specific quality metrics"""
        try:
            # Get image dimensions and DPI
            width, height = pil_image.size
            dpi = pil_image.info.get('dpi', (72, 72))[0] if 'dpi' in pil_image.info else 72
            
            # Load image with OpenCV for analysis
            cv_image = cv2.imread(image_path)
            if cv_image is None:
                # Try converting PIL to OpenCV
                cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Calculate clarity using Laplacian variance
            clarity_score = cv2.Laplacian(gray, cv2.CV_64F).var()
            # Normalize clarity score (typical range 0-2000, normalize to 0-1)
            normalized_clarity = min(clarity_score / 1000.0, 1.0)
            
            # Calculate contrast
            contrast = gray.std()
            normalized_contrast = min(contrast / 128.0, 1.0)
            
            # Calculate brightness distribution
            brightness_mean = gray.mean()
            brightness_score = 1.0 - abs(brightness_mean - 128) / 128.0  # Optimal around 128
            
            # Detect noise level
            noise_level = self._estimate_noise_level(gray)
            
            return {
                "width": width,
                "height": height,
                "dpi": dpi,
                "clarity_score": normalized_clarity,
                "contrast": normalized_contrast,
                "brightness_score": brightness_score,
                "noise_level": noise_level,
                "total_pixels": width * height
            }
            
        except Exception as e:
            logger.error(f"Error assessing image quality: {str(e)}")
            return {
                "width": 0,
                "height": 0,
                "dpi": 0,
                "clarity_score": 0.0,
                "contrast": 0.0,
                "brightness_score": 0.0,
                "noise_level": 1.0,
                "total_pixels": 0
            }
    
    def _assess_text_quality(self, image_path: str) -> Dict[str, Any]:
        """Assess text-specific quality metrics"""
        try:
            # Get OCR confidence data
            ocr_data = pytesseract.image_to_data(image_path, output_type=pytesseract.Output.DICT)
            
            # Calculate text density and confidence
            confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
            text_blocks = [text for text in ocr_data['text'] if text.strip()]
            
            if not confidences:
                return {
                    "text_density": 0.0,
                    "avg_confidence": 0.0,
                    "text_blocks_count": 0,
                    "readable_text_ratio": 0.0
                }
            
            avg_confidence = sum(confidences) / len(confidences)
            text_density = len(text_blocks) / max(len(ocr_data['text']), 1)
            
            # Calculate readable text ratio (confidence > 60)
            readable_blocks = [conf for conf in confidences if conf > 60]
            readable_ratio = len(readable_blocks) / len(confidences) if confidences else 0.0
            
            # Estimate text coverage area
            total_area = 0
            text_area = 0
            
            for i, conf in enumerate(ocr_data['conf']):
                if int(conf) > 0:
                    w = int(ocr_data['width'][i])
                    h = int(ocr_data['height'][i])
                    area = w * h
                    total_area += area
                    if int(conf) > 30:  # Consider as text if confidence > 30
                        text_area += area
            
            text_coverage = text_area / max(total_area, 1)
            
            return {
                "text_density": text_density,
                "avg_confidence": avg_confidence / 100.0,  # Normalize to 0-1
                "text_blocks_count": len(text_blocks),
                "readable_text_ratio": readable_ratio,
                "text_coverage": text_coverage
            }
            
        except Exception as e:
            logger.error(f"Error assessing text quality: {str(e)}")
            return {
                "text_density": 0.0,
                "avg_confidence": 0.0,
                "text_blocks_count": 0,
                "readable_text_ratio": 0.0,
                "text_coverage": 0.0
            }
    
    def _estimate_noise_level(self, gray_image: np.ndarray) -> float:
        """Estimate noise level in the image"""
        try:
            # Use median filter to estimate noise
            median_filtered = cv2.medianBlur(gray_image, 5)
            noise = cv2.absdiff(gray_image, median_filtered)
            noise_level = noise.mean() / 255.0  # Normalize to 0-1
            return noise_level
        except Exception:
            return 0.5  # Default moderate noise level
    
    def _calculate_overall_score(self, image_metrics: Dict[str, Any], text_metrics: Dict[str, Any]) -> float:
        """Calculate overall quality score from individual metrics"""
        try:
            # Weight different factors
            weights = {
                "dpi": 0.2,
                "clarity": 0.25,
                "contrast": 0.15,
                "brightness": 0.1,
                "noise": 0.1,
                "text_confidence": 0.15,
                "text_density": 0.05
            }
            
            # Normalize DPI score
            dpi_score = min(image_metrics.get("dpi", 0) / self.min_dpi, 1.0)
            
            # Get other scores
            clarity_score = image_metrics.get("clarity_score", 0.0)
            contrast_score = image_metrics.get("contrast", 0.0)
            brightness_score = image_metrics.get("brightness_score", 0.0)
            noise_score = 1.0 - image_metrics.get("noise_level", 0.5)  # Invert noise (less is better)
            text_confidence = text_metrics.get("avg_confidence", 0.0)
            text_density = text_metrics.get("text_density", 0.0)
            
            # Calculate weighted score
            overall_score = (
                weights["dpi"] * dpi_score +
                weights["clarity"] * clarity_score +
                weights["contrast"] * contrast_score +
                weights["brightness"] * brightness_score +
                weights["noise"] * noise_score +
                weights["text_confidence"] * text_confidence +
                weights["text_density"] * text_density
            )
            
            return min(overall_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating overall score: {str(e)}")
            return 0.0
    
    def _identify_issues(self, image_metrics: Dict[str, Any], text_metrics: Dict[str, Any]) -> List[str]:
        """Identify specific quality issues"""
        issues = []
        
        # DPI issues
        dpi = image_metrics.get("dpi", 0)
        if dpi < self.min_dpi:
            issues.append(f"Low resolution: {dpi} DPI (recommended: {self.min_dpi}+ DPI)")
        
        # Clarity issues
        clarity = image_metrics.get("clarity_score", 0.0)
        if clarity < self.min_clarity_score:
            issues.append(f"Poor image clarity: {clarity:.2f} (recommended: {self.min_clarity_score}+)")
        
        # Contrast issues
        contrast = image_metrics.get("contrast", 0.0)
        if contrast < 0.3:
            issues.append("Low contrast - text may be difficult to read")
        
        # Brightness issues
        brightness = image_metrics.get("brightness_score", 0.0)
        if brightness < 0.5:
            issues.append("Poor brightness balance - image may be too dark or too bright")
        
        # Noise issues
        noise = image_metrics.get("noise_level", 0.0)
        if noise > 0.3:
            issues.append("High noise level detected - may affect text recognition")
        
        # Text issues
        text_confidence = text_metrics.get("avg_confidence", 0.0)
        if text_confidence < 0.6:
            issues.append(f"Low OCR confidence: {text_confidence:.2f} (recommended: 0.6+)")
        
        text_density = text_metrics.get("text_density", 0.0)
        if text_density < self.min_text_density:
            issues.append("Low text density - document may be mostly blank or contain non-text content")
        
        return issues
    
    def _generate_recommendations(self, image_metrics: Dict[str, Any], text_metrics: Dict[str, Any], overall_score: float) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        if overall_score < 0.3:
            recommendations.append("Document quality is very poor - consider re-scanning at higher quality")
        elif overall_score < 0.6:
            recommendations.append("Document quality is below optimal - improvements recommended")
        
        # Specific recommendations
        dpi = image_metrics.get("dpi", 0)
        if dpi < self.min_dpi:
            recommendations.append(f"Scan at higher resolution (minimum {self.min_dpi} DPI)")
        
        clarity = image_metrics.get("clarity_score", 0.0)
        if clarity < self.min_clarity_score:
            recommendations.append("Ensure document is in focus and scanner glass is clean")
        
        contrast = image_metrics.get("contrast", 0.0)
        if contrast < 0.3:
            recommendations.append("Increase contrast settings or use better lighting")
        
        brightness = image_metrics.get("brightness_score", 0.0)
        if brightness < 0.5:
            recommendations.append("Adjust brightness settings for better balance")
        
        noise = image_metrics.get("noise_level", 0.0)
        if noise > 0.3:
            recommendations.append("Reduce noise by using better scanning settings or cleaning the document")
        
        text_confidence = text_metrics.get("avg_confidence", 0.0)
        if text_confidence < 0.6:
            recommendations.append("Improve text clarity - check for smudges, folds, or poor print quality")
        
        if not recommendations:
            recommendations.append("Document quality is acceptable for processing")
        
        return recommendations