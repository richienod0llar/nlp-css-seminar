"""Load Qwen3.5-9B from shared storage and run one short prompt."""

import os

# Avoid cuDNN SDPA init issues on some LRZ GPU stacks (see CUDNN_STATUS_NOT_INITIALIZED).
os.environ.setdefault("TORCH_CUDNN_SDPA_ENABLED", "0")

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

MODEL_PATH = "/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3.5-9B"
PROMPT = "You are a helpful assistant. User: Say hello in one sentence. Assistant:"

print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

print(f"Loading model from {MODEL_PATH} ...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    trust_remote_code=True,
    attn_implementation="eager",  # safer than default SDPA on LRZ H100 stack
)

inputs = tokenizer(PROMPT, return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=40, do_sample=False)
print("\n--- Output ---")
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
