import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found in .env file")
    exit()

try:
    client = genai.Client(api_key=api_key)
    print("\n--- Available Gemini Models for your Key ---")
    
    # List models and filter for those that generate content
    for model in client.models.list():
        # We only care about models we can chat with (generateContent)
        if "generateContent" in model.supported_actions:
            print(f"- {model.name} ({model.display_name})")
            
except Exception as e:
    print(f"Error fetching models: {e}")