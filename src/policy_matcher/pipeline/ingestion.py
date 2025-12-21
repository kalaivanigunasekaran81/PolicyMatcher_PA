import fitz  # pymupdf
from typing import List, Dict, Any, Optional
import re
import uuid

class PDFProcessor:
    """Extracts text and structure from PDF policies."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        
    def extract_text(self) -> str:
        """Extracts full text from the PDF."""
        doc = fitz.open(self.file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text

    def extract_metadata(self) -> Dict[str, Any]:
        """
        Extracts metadata such as Policy Number, Effective Date, and Version.
        """
        text = self.extract_text()
        metadata = {
            "source": self.file_path,
            "policy_number": None,
            "effective_date": None,
            "version": None
        }

        # Regex patterns for common metadata
        # Prototype: Basic patterns, can be improved with OCR/Layout analysis later
        
        # Policy Number: e.g., "Policy Number: 12345" or "Policy #: X"
        policy_num_match = re.search(r"(?i)Policy\s*(?:Number|#)[:\.]?\s*([A-Z0-9\-]+)", text)
        if policy_num_match:
            metadata["policy_number"] = policy_num_match.group(1)

        # Effective Date: e.g., "Effective Date: 01/01/2023"
        date_match = re.search(r"(?i)Effective\s*Date[:\.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})", text)
        if date_match:
            metadata["effective_date"] = date_match.group(1)

        # Version: e.g., "Version 1.0"
        version_match = re.search(r"(?i)Version[:\.]?\s*(\d+(\.\d+)?)", text)
        if version_match:
            metadata["version"] = version_match.group(1)
            
        return metadata

    def extract_filtered_text(self) -> str:
        """
        Extracts text specifically from the 'Policy' section.
        """
        full_text = self.extract_text()
        
        # 1. Locate "Policy" Header
        # Note: We look for "Policy" followed immediately by text, or as a standalone line.
        # This regex looks for the word Policy on its own line or followed by non-alpha chars
        match = re.search(r"(?i)\n\s*Policy\s*\n", full_text)
        if not match:
             # Fallback: Try just text "Policy"
             match = re.search(r"Policy", full_text)
             
        if not match:
            print("Warning: 'Policy' section header not found. Using full text.")
            return full_text
            
        start_index = match.end()
        
        # 2. Locate End of Section
        # Stop at common next sections like "References", "Coding", "Background"
        end_regex = re.compile(r"(?i)\n\s*(References|Coding|Background|Procedure Codes|Diagnosis Codes)\s*")
        end_match = end_regex.search(full_text, start_index)
        
        if end_match:
            policy_text = full_text[start_index:end_match.start()]
        else:
            policy_text = full_text[start_index:]
            
        return policy_text.strip()

class SmartChunker:
    """Splits policy text into retrievable chunks (rules) and classifies them."""
    
    def _classify_text(self, text: str) -> str:
        """
        Classifies the policy text chunk into a category:
        - Exclusions
        - Required Documentation
        - Medical Necessity
        - Eligibility
        """
        text_lower = text.lower()
        
        # Heuristic 1: Exclusions (Priority 1: Negatives often override positives)
        exclusion_keywords = [
            "not medically necessary", "investigational", "experimental", 
            "unproven", "not covered", "exclusion", "contraindicated"
        ]
        if any(k in text_lower for k in exclusion_keywords):
            return "Exclusions"
            
        # Heuristic 2: Documentation
        doc_keywords = ["documentation", "medical record", "submit"]
        if any(k in text_lower for k in doc_keywords):
            return "Required Documentation"
            
        # Heuristic 3: Medical Necessity (Positive assertion)
        med_nec_keywords = ["medically necessary", "medical necessity"]
        if any(k in text_lower for k in med_nec_keywords):
            return "Medical Necessity"
            
        # Heuristic 4: Eligibility / Criteria (Default bucket for "Candidates", "Indications")
        return "Eligibility"

    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        Splits text into chunks based on numbered lists (1., 2., etc).
        """
        lines = text.split('\n')
        chunks = []
        current_chunk_text = []
        current_chunk_id = 0
        
        # Regex to identify "1." or "10." at start of line
        rule_start_pattern = re.compile(r"^\s*\d+\.\s+")
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
                
            if rule_start_pattern.match(stripped):
                # Save previous chunk if exists
                if current_chunk_text:
                    full_chunk_text = "\n".join(current_chunk_text).strip()
                    rule_type = self._classify_text(full_chunk_text)
                    chunks.append({
                        "id": f"rule_{current_chunk_id}",
                        "text": full_chunk_text,
                        "metadata": {
                            "type": "policy_criteria",
                            "rule_type": rule_type
                        }
                    })
                
                # Start new chunk
                current_chunk_id += 1
                current_chunk_text = [stripped]
            else:
                # Append to current chunk (sub-items or continuation)
                if current_chunk_text:
                    current_chunk_text.append(stripped)
        
        # Add the last chunk
        if current_chunk_text:
            full_chunk_text = "\n".join(current_chunk_text).strip()
            rule_type = self._classify_text(full_chunk_text)
            chunks.append({
                "id": f"rule_{current_chunk_id}",
                "text": full_chunk_text,
                "metadata": {
                    "type": "policy_criteria",
                    "rule_type": rule_type
                }
            })
            
        return chunks
