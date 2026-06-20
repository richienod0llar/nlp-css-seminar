import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, List, Optional

from src.sig.schema import GoldRow, ConceptRule


def load_concept_names(yaml_path: str) -> List[str]:
    """Return canonical basic concept names from concepts.yaml."""
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return list(data["Concepts"].keys())


class DataManager:
    def __init__(self, excel_path: str, yaml_path: str):
        self.excel_path = Path(excel_path)
        self.yaml_path = Path(yaml_path)
        self.concepts: Dict[str, ConceptRule] = {}
        self.gold_data: List[GoldRow] = []

    def load_all(self):
        self._load_yaml()
        self._load_excel()

    def _load_yaml(self):
        with open(self.yaml_path, 'r') as f:
            data = yaml.safe_load(f)
            for name, info in data['Concepts'].items():
                self.concepts[name] = ConceptRule(
                    name=name,
                    type=info['type'],
                    allowed_structures=info['structures']
                )
                
    def _load_excel(self):
        df = pd.read_excel(self.excel_path)
        for _, row in df.iterrows():
            self.gold_data.append(GoldRow(
                example_id=int(row['example_id']),
                input_indicator=str(row['input_indicator']),
                basic_concept=str(row['basic_concept']),
                semantic_structure=str(row['semantic_structure']),
                assertion=str(row['assertion']),
                question=str(row['question']),
                answer_options=str(row['answer_options']) if pd.notna(row['answer_options']) else None,
                domain=str(row['domain']),
                source_type=str(row['source_type']),
                confusable_with=str(row['confusable_with']) if pd.notna(row['confusable_with']) else None
            ))

    def get_row_by_id(self, example_id: int) -> Optional[GoldRow]:
        return next((r for r in self.gold_data if r.example_id == example_id), None)