import openai
print("OpenAI version:", openai.__version__)

try:
    openai.ChatCompletion.create(model="gpt-4o-mini", messages=[])
except Exception as e:
    print(f"Caught expected error: {e}")
