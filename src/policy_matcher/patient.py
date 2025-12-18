from typing import List, Optional
from pydantic import BaseModel, Field

class PatientContext(BaseModel):
    """Normalized patient data structure."""
    age: int
    gender: str
    diagnosis_codes: List[str] = Field(description="List of ICD-10 codes")
    procedure_codes: List[str] = Field(description="List of CPT/HCPCS codes")
    prior_treatments: List[str] = Field(default_factory=list, description="Normalized treatment names")
    imaging_reports: List[str] = Field(default_factory=list, description="Imaging findings")
    medications: List[str] = Field(default_factory=list)

def normalize_features(raw_data: dict) -> PatientContext:
    """
    Normalizes raw patient data into the PatientContext model.
    In a real system, this would look up code hierarchies (ICD, CPT, RxNorm).
    """
    # Prototype: Direct mapping with simple validation/cleanup
    return PatientContext(
        age=raw_data.get("age", 0),
        gender=raw_data.get("gender", "UNKNOWN"),
        diagnosis_codes=[c.strip().upper() for c in raw_data.get("diagnosis_codes", [])],
        procedure_codes=[c.strip().upper() for c in raw_data.get("procedure_codes", [])],
        prior_treatments=[t.lower().strip() for t in raw_data.get("prior_treatments", [])],
        imaging_reports=raw_data.get("imaging", []),
        medications=raw_data.get("medications", [])
    )
