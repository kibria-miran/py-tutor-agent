import sys, config
from openai import OpenAI
model = sys.argv[1]
c = OpenAI(base_url=config.API_BASE, api_key=config.NVIDIA_API_KEY, timeout=config.API_TIMEOUT)
tools = [{"type": "function", "function": {"name": "add", "description": "Add two integers.",
  "parameters": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}}}]
r = c.chat.completions.create(model=model, messages=[{"role": "user", "content": "Use the add tool for 2 and 3."}], tools=tools, tool_choice="auto")
m = r.choices[0].message
print("TOOL CALLS:", m.tool_calls)
print("TEXT:", m.content)
