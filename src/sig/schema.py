from dataclasses import dataclass
from typing import List, Optional, Dict

@dataclass
class GoldRow:
    example_id: int
    input_indicator: str
    basic_concept: str
    semantic_structure: str
    assertion: str
    question: str
    answer_options: Optional[str]
    source_type: str
    domain: str
    confusable_with: Optional[str] = None
    
@dataclass
class ConceptRule:
    name: str
    type: str # subjective or objective
    allowed_structures: Dict[int, Optional[str]]

@dataclass
class AssertionResult:
    predicted_concept: str
    predicted_structure_code: str
    predicted_assertion: str
    raw_response: str

@dataclass
class QuestionResult:
    predicted_question:str
    predicted_options: Optional[str]
    question_format: str
    raw_response: str

