import os
from dotenv import load_dotenv, find_dotenv
from groq import Groq

print("Using .env file:", find_dotenv())
load_dotenv()

key = os.getenv("GROQ_API_KEY")
if not key or not key.startswith("gsk_"):
    print("Problem: no valid key found. Check your .env file.")
else:
    print("Key found, starts with:", key[:6])
    client = Groq(api_key=key)
    for m in client.models.list().data:
        print(m.id)