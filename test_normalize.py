"""Structure-code extraction must keep codes that differ only in a suffix distinct.

Run: python test_normalize.py
"""

from src.sig.normalize import concepts_match, extract_structure_code, structures_match

ex = extract_structure_code

# Codes that used to collapse into each other (Procedures -> Place, xP(e)y -> xP).
assert ex("xDpl, pro") != ex("xDpl"), "Procedures and Place must not share a code"
assert ex("xP(e)y") != ex("xP(e)"), "xP(e)y and xP(e) must stay distinct"
assert ex("xP(e)y") != ex("xP"), "xP(e)y must not truncate to xP"

# Codes are extracted whole, from bare labels and from prose.
assert ex("xIe") == "xie"
assert ex("g(H+I)y") == "g(h+i)y"
assert ex("o(H+I)y") == "o(h+i)y"
assert ex("Structure code: xPRy") == "xpry"
assert ex("xDpl, pro") == "xdpl,pro"

# Case and whitespace differences between gold and prediction do not matter.
assert structures_match("xDpl, pro", "xdpl,  pro")
assert structures_match("xIe", "  xIe  ")
assert not structures_match("xDpl", "xDpl, pro")
assert not structures_match("xIe", "xIi")
assert ex("") == "" and ex(None) == ""

# Concept matching still unifies US/UK spelling against the canonical YAML names.
CONCEPTS = ["Behaviour", "Cognitive judgement", "Evaluation"]
assert concepts_match("Behavior", "Behaviour", CONCEPTS)
assert concepts_match("Cognitive judgment", "Cognitive judgement", CONCEPTS)
assert not concepts_match("Evaluation", "Behaviour", CONCEPTS)

print("normalize ok")
