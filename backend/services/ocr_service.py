import pytesseract
import easyocr
from PIL import Image
from pdf2image import convert_from_path
import os
import tempfile
from typing import List, Tuple, Dict, Any
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        self.ocr_engine = os.getenv("OCR_ENGINE", "tesseract")
        self.tesseract_cmd = os.getenv("TESSERACT_CMD", "/usr/bin/tesseract")
        
        # Configure Tesseract
        if self.ocr_engine == "tesseract":
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        
        # Initialize EasyOCR reader if needed
        self.easyocr_reader = None
        if self.ocr_engine == "easyocr":
            self.easyocr_reader = easyocr.Reader(['en'])
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text from PDF using OCR
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing extracted text, confidence, and metadata
        """
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=300)
            
            all_text = []
            all_confidences = []
            page_results = []
            
            for page_num, image in enumerate(images, 1):
                logger.info(f"Processing page {page_num} of {len(images)}")
                
                # Save image temporarily
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    image.save(temp_file.name, 'PNG')
                    temp_image_path = temp_file.name
                
                try:
                    # Extract text based on OCR engine
                    if self.ocr_engine == "tesseract":
                        page_result = self._extract_with_tesseract(temp_image_path)
                    else:
                        page_result = self._extract_with_easyocr(temp_image_path)
                    
                    page_result['page_number'] = page_num
                    page_results.append(page_result)
                    
                    all_text.append(page_result['text'])
                    all_confidences.append(page_result['confidence'])
                    
                finally:
                    # Clean up temporary file
                    os.unlink(temp_image_path)
            
            # Calculate overall confidence
            overall_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
            
            return {
                'text': '\n\n--- PAGE BREAK ---\n\n'.join(all_text),
                'confidence': overall_confidence,
                'engine': self.ocr_engine,
                'page_count': len(images),
                'page_results': page_results
            }
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise Exception(f"OCR processing failed: {str(e)}")
    
    def _extract_with_tesseract(self, image_path: str) -> Dict[str, Any]:
        """Extract text using Tesseract OCR"""
        try:
            # Get text with confidence data
            data = pytesseract.image_to_data(
                image_path, 
                output_type=pytesseract.Output.DICT,
                config='--psm 6'  # Assume uniform block of text
            )
            
            # Extract text and calculate confidence
            text_parts = []
            confidences = []
            
            for i, conf in enumerate(data['conf']):
                if int(conf) > 0:  # Only include confident detections
                    word = data['text'][i].strip()
                    if word:
                        text_parts.append(word)
                        confidences.append(int(conf))
            
            text = ' '.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                'text': text,
                'confidence': avg_confidence / 100.0,  # Convert to 0-1 scale
                'word_count': len(text_parts),
                'raw_data': data
            }
            
        except Exception as e:
            logger.error(f"Tesseract OCR error: {str(e)}")
            return {
                'text': '',
                'confidence': 0.0,
                'word_count': 0,
                'error': str(e)
            }
    
    def _extract_with_easyocr(self, image_path: str) -> Dict[str, Any]:
        """Extract text using EasyOCR"""
        try:
            results = self.easyocr_reader.readtext(image_path)
            
            text_parts = []
            confidences = []
            
            for (bbox, text, confidence) in results:
                if confidence > 0.5:  # Only include confident detections
                    text_parts.append(text)
                    confidences.append(confidence)
            
            text = ' '.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                'text': text,
                'confidence': avg_confidence,
                'word_count': len(text_parts),
                'raw_results': results
            }
            
        except Exception as e:
            logger.error(f"EasyOCR error: {str(e)}")
            return {
                'text': '',
                'confidence': 0.0,
                'word_count': 0,
                'error': str(e)
            }
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess OCR text for better LLM processing
        
        Args:
            text: Raw OCR text
            
        Returns:
            Cleaned and preprocessed text
        """
        if not text:
            return ""
        
        # Basic text cleaning
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 1:  # Skip very short lines
                # Remove excessive whitespace
                line = ' '.join(line.split())
                cleaned_lines.append(line)
        
        # Join lines with proper spacing
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Remove excessive line breaks
        while '\n\n\n' in cleaned_text:
            cleaned_text = cleaned_text.replace('\n\n\n', '\n\n')
        
        return cleaned_text
    
    def chunk_text(self, text: str, max_chunk_size: int = 4000) -> List[str]:
        """
        Chunk text for LLM processing while preserving context
        
        Args:
            text: Text to chunk
            max_chunk_size: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed limit
            if len(current_chunk) + len(paragraph) + 2 > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    # Paragraph itself is too long, split by sentences
                    sentences = paragraph.split('. ')
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 2 > max_chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                current_chunk = sentence
                            else:
                                # Even sentence is too long, force split
                                chunks.append(sentence[:max_chunk_size])
                                current_chunk = sentence[max_chunk_size:]
                        else:
                            current_chunk += sentence + '. '
            else:
                current_chunk += paragraph + '\n\n'
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks