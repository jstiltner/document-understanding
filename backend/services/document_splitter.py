import logging
from typing import Dict, Any, List
import cv2
import numpy as np
from PIL import Image
import os
import tempfile
from pdf2image import convert_from_path
import pytesseract

logger = logging.getLogger(__name__)

class DocumentSplitterService:
    """Service for splitting multi-document files into individual documents"""
    
    def __init__(self):
        self.min_page_height = 500  # Minimum height for a valid page
        self.separator_threshold = 0.8  # Threshold for detecting page separators
        self.confidence_threshold = 0.7  # Minimum confidence for split detection
    
    def split_document(self, file_path: str) -> Dict[str, Any]:
        """
        Split a multi-document file into individual documents
        
        Args:
            file_path: Path to the document file to split
            
        Returns:
            Dictionary containing split results and individual document paths
        """
        try:
            if file_path.lower().endswith('.pdf'):
                return self._split_pdf_document(file_path)
            else:
                return self._split_image_document(file_path)
                
        except Exception as e:
            logger.error(f"Error splitting document: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "documents": []
            }
    
    def _split_pdf_document(self, pdf_path: str) -> Dict[str, Any]:
        """Split a PDF document into individual documents"""
        
        try:
            # Convert PDF pages to images
            images = convert_from_path(pdf_path, dpi=200)
            
            if len(images) <= 1:
                return {
                    "status": "no_split_needed",
                    "message": "Document has only one page",
                    "documents": [{
                        "file_path": pdf_path,
                        "file_size": os.path.getsize(pdf_path),
                        "page_range": "1-1",
                        "confidence": 1.0
                    }]
                }
            
            # Analyze pages to find document boundaries
            split_points = self._detect_document_boundaries(images)
            
            if not split_points:
                return {
                    "status": "no_split_detected",
                    "message": "No document boundaries detected",
                    "documents": [{
                        "file_path": pdf_path,
                        "file_size": os.path.getsize(pdf_path),
                        "page_range": f"1-{len(images)}",
                        "confidence": 0.5
                    }]
                }
            
            # Create individual documents
            documents = []
            base_name = os.path.splitext(pdf_path)[0]
            
            start_page = 0
            for i, split_point in enumerate(split_points + [len(images)]):
                if split_point > start_page:
                    # Create document for this range
                    doc_images = images[start_page:split_point]
                    doc_path = f"{base_name}_part_{i+1}.pdf"
                    
                    # Save as PDF (would need additional PDF library for this)
                    # For now, save as images
                    doc_path = f"{base_name}_part_{i+1}.png"
                    if len(doc_images) == 1:
                        doc_images[0].save(doc_path)
                    else:
                        # Combine multiple images into one (simple vertical stack)
                        combined_image = self._combine_images_vertically(doc_images)
                        combined_image.save(doc_path)
                    
                    documents.append({
                        "file_path": doc_path,
                        "file_size": os.path.getsize(doc_path),
                        "page_range": f"{start_page+1}-{split_point}",
                        "confidence": 0.8,
                        "pages_count": len(doc_images)
                    })
                    
                    start_page = split_point
            
            return {
                "status": "split_completed",
                "original_pages": len(images),
                "documents_created": len(documents),
                "documents": documents
            }
            
        except Exception as e:
            logger.error(f"Error splitting PDF: {str(e)}")
            raise
    
    def _split_image_document(self, image_path: str) -> Dict[str, Any]:
        """Split a single image that may contain multiple documents"""
        
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Could not load image")
            
            # Detect horizontal separators (common in faxed documents)
            separators = self._detect_horizontal_separators(image)
            
            if not separators:
                return {
                    "status": "no_split_needed",
                    "message": "No document separators detected",
                    "documents": [{
                        "file_path": image_path,
                        "file_size": os.path.getsize(image_path),
                        "confidence": 1.0
                    }]
                }
            
            # Split image at separator points
            documents = []
            base_name = os.path.splitext(image_path)[0]
            
            y_start = 0
            for i, separator_y in enumerate(separators + [image.shape[0]]):
                if separator_y > y_start + self.min_page_height:
                    # Extract document region
                    doc_region = image[y_start:separator_y, :]
                    
                    # Save as separate image
                    doc_path = f"{base_name}_part_{i+1}.png"
                    cv2.imwrite(doc_path, doc_region)
                    
                    documents.append({
                        "file_path": doc_path,
                        "file_size": os.path.getsize(doc_path),
                        "region": f"y:{y_start}-{separator_y}",
                        "confidence": 0.8,
                        "height": separator_y - y_start
                    })
                    
                    y_start = separator_y
            
            return {
                "status": "split_completed",
                "original_size": f"{image.shape[1]}x{image.shape[0]}",
                "documents_created": len(documents),
                "documents": documents
            }
            
        except Exception as e:
            logger.error(f"Error splitting image: {str(e)}")
            raise
    
    def _detect_document_boundaries(self, images: List[Image.Image]) -> List[int]:
        """Detect document boundaries in a list of PDF page images"""
        
        split_points = []
        
        try:
            for i, image in enumerate(images):
                # Convert PIL image to OpenCV format
                cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # Look for document boundary indicators
                if self._is_document_boundary(cv_image, i):
                    split_points.append(i)
            
            return split_points
            
        except Exception as e:
            logger.error(f"Error detecting document boundaries: {str(e)}")
            return []
    
    def _is_document_boundary(self, image: np.ndarray, page_index: int) -> bool:
        """Determine if a page represents a document boundary"""
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Look for common boundary indicators
            
            # 1. Check for mostly blank pages (common separator)
            non_white_pixels = np.sum(gray < 240)
            total_pixels = gray.shape[0] * gray.shape[1]
            content_ratio = non_white_pixels / total_pixels
            
            if content_ratio < 0.05:  # Less than 5% content
                return True
            
            # 2. Look for header patterns that indicate new documents
            header_region = gray[:int(gray.shape[0] * 0.2), :]  # Top 20%
            
            # Use OCR to detect common header text
            try:
                header_text = pytesseract.image_to_string(header_region).lower()
                
                # Common document start indicators
                start_indicators = [
                    "authorization", "denial", "approval", "notice",
                    "patient:", "member:", "case:", "reference:",
                    "date:", "to:", "from:", "re:"
                ]
                
                header_score = sum(1 for indicator in start_indicators if indicator in header_text)
                
                if header_score >= 2:  # Multiple indicators suggest document start
                    return True
                    
            except Exception:
                pass  # OCR failed, continue with other methods
            
            # 3. Look for visual patterns (logos, letterheads)
            # This is a simplified approach - could be more sophisticated
            top_region = gray[:int(gray.shape[0] * 0.15), :]
            
            # Detect potential logo/letterhead regions (high contrast areas)
            edges = cv2.Canny(top_region, 50, 150)
            edge_density = np.sum(edges > 0) / (top_region.shape[0] * top_region.shape[1])
            
            if edge_density > 0.02:  # Significant edge content in header
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking document boundary: {str(e)}")
            return False
    
    def _detect_horizontal_separators(self, image: np.ndarray) -> List[int]:
        """Detect horizontal separators in an image"""
        
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Look for horizontal lines that span most of the width
            height, width = gray.shape
            
            separators = []
            
            # Scan for horizontal lines
            for y in range(int(height * 0.1), int(height * 0.9), 10):  # Skip top/bottom 10%
                row = gray[y, :]
                
                # Look for long sequences of similar pixels (potential separator lines)
                # or very light/white regions (blank space between documents)
                
                # Method 1: Detect horizontal lines
                line_pixels = np.sum(row < 50)  # Dark pixels
                if line_pixels > width * 0.8:  # Line spans 80% of width
                    separators.append(y)
                    continue
                
                # Method 2: Detect blank regions
                blank_pixels = np.sum(row > 240)  # Very light pixels
                if blank_pixels > width * 0.9:  # 90% blank
                    # Check if this is part of a larger blank region
                    blank_region_height = 0
                    for check_y in range(max(0, y-20), min(height, y+20)):
                        check_row = gray[check_y, :]
                        if np.sum(check_row > 240) > width * 0.9:
                            blank_region_height += 1
                    
                    if blank_region_height > 10:  # Significant blank region
                        separators.append(y)
            
            # Remove separators that are too close together
            filtered_separators = []
            for sep in separators:
                if not filtered_separators or sep - filtered_separators[-1] > self.min_page_height:
                    filtered_separators.append(sep)
            
            return filtered_separators
            
        except Exception as e:
            logger.error(f"Error detecting horizontal separators: {str(e)}")
            return []
    
    def _combine_images_vertically(self, images: List[Image.Image]) -> Image.Image:
        """Combine multiple images vertically into one image"""
        
        try:
            if not images:
                raise ValueError("No images to combine")
            
            if len(images) == 1:
                return images[0]
            
            # Calculate total height and max width
            total_height = sum(img.height for img in images)
            max_width = max(img.width for img in images)
            
            # Create combined image
            combined = Image.new('RGB', (max_width, total_height), 'white')
            
            # Paste images vertically
            y_offset = 0
            for img in images:
                # Center image horizontally if it's narrower
                x_offset = (max_width - img.width) // 2
                combined.paste(img, (x_offset, y_offset))
                y_offset += img.height
            
            return combined
            
        except Exception as e:
            logger.error(f"Error combining images: {str(e)}")
            return images[0] if images else None
    
    def classify_document_type(self, image_path: str) -> Dict[str, Any]:
        """
        Classify the type of document (authorization, denial, etc.)
        This is a basic implementation that could be enhanced with ML
        """
        
        try:
            # Extract text from document
            text = pytesseract.image_to_string(image_path).lower()
            
            # Simple keyword-based classification
            classification_rules = {
                "authorization": ["authorization", "approved", "authorize", "approval"],
                "denial": ["denial", "denied", "reject", "decline", "not approved"],
                "appeal": ["appeal", "reconsideration", "review request"],
                "claim": ["claim", "billing", "invoice", "payment"],
                "correspondence": ["letter", "notice", "communication", "memo"]
            }
            
            scores = {}
            for doc_type, keywords in classification_rules.items():
                score = sum(1 for keyword in keywords if keyword in text)
                scores[doc_type] = score
            
            # Find best match
            if scores:
                best_type = max(scores.keys(), key=lambda k: scores[k])
                confidence = scores[best_type] / len(classification_rules[best_type])
                
                return {
                    "document_type": best_type,
                    "confidence": min(confidence, 1.0),
                    "all_scores": scores
                }
            
            return {
                "document_type": "unknown",
                "confidence": 0.0,
                "all_scores": scores
            }
            
        except Exception as e:
            logger.error(f"Error classifying document: {str(e)}")
            return {
                "document_type": "unknown",
                "confidence": 0.0,
                "error": str(e)
            }