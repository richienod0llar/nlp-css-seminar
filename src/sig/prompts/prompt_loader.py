import yaml
from pathlib import Path
from typing import Dict, Any, Union

def load_concepts_block(yaml_path: Union[str, Path]) -> str:
    """
    Reads concept.yaml and formats into a human-readable
    block suitable for injection into a system prompt.
    """

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    notation = data.get('notation', {})
    concepts = data.get('Concepts', {})
    structures = data.get('structures', {})

    lines = []

    # --Notation Key--
    lines.append("# NOTATION KEY")
    for symbol, meaning in notation.items():
        lines.append(f"{symbol} = {meaning}")
    lines.append("")

    # --Structure Definitions--
    lines.append("# STRUCTURE DEFINITIONS")

    if isinstance(structures, dict):
        for code, description in structures.items():
            lines.append(f"Structure {code} = {description}")
    elif isinstance(structures, str): 
        lines.append(structures)
        
    lines.append("")

    # --Concepts--
    lines.append("# BASIC CONCEPTS AND ALLOWED STRUCTURES")
    lines.append("You must ONLY use the structure code listed under each concept.\n")

    subjective = {k: v for k, v in concepts.items() if v.get('type') == 'subjective'}
    objective = {k: v for k, v in concepts.items() if v.get('type') == 'objective'}

    lines.append("## Subjective Concepts")
    for name, info in subjective.items():
        # structures is a dict with 'None' values
        allowed = [code for code in info.get('structures', {}).values() if code is not None]
        lines.append(f" -{name} → {','.join(allowed)}")

    lines.append("")
    lines.append("## Objective Concepts")
    for name, info in objective.items():
        allowed = [code for code in info.get('structures', {}).values() if code is not None]
        lines.append(f" -{name} → {','.join(allowed)}")

    return "\n".join(lines)

def load_prompt(template_path: Union[str, Path], yaml_path: Union[str, Path]) -> str:
    """
    Loads a prompt template and insert the concepts block
    wherever the placeholder {{CONCEPTS_BLOCK}} appears.
    """
    template = Path(template_path).read_text(encoding="utf-8")
    concepts_block = load_concepts_block(yaml_path)
    return template.replace("{{CONCEPTS_BLOCK}}", concepts_block)