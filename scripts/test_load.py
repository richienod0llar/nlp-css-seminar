import yaml
from src.sig.loader import DataManager
from src.sig.llm_client import get_client

# Initialize the manager
manager = DataManager(excel_path='data/gold_set.xlsx', yaml_path='data/concepts.yaml')
manager.load_all()

# Test a Row
row = manager.get_row_by_id(1)
print(f"Row 1 indicator: {row.input_indicator}")
print(f"Row 1 Concept: {row.basic_concept}")

# Test a Rule
rule = manager.concepts.get(row.basic_concept)
print(f"Allowed Structures for {row.basic_concept}: {rule.allowed_structures}")

config = yaml.safe_load(open("config.yaml"))
client = get_client(config, mock=True)

# Simulate an Assertion Developer call
response = client.chat_completion(
    system_prompt="You are an assertion developer...",
    user_prompt="Input indicator: Overall satisfaction with product"
)
print(response)