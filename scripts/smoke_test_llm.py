"""Call the local vLLM OpenAI-compatible API."""

from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")

models = client.models.list()
print("Models:", [m.id for m in models.data])

response = client.chat.completions.create(
    model=models.data[0].id,
    messages=[{"role": "user", "content": "Say hello in one sentence."}],
    max_tokens=40,
)
print("\n--- Response ---")
print(response.choices[0].message.content)
