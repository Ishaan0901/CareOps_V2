#   For Gemini

# import os
# from dotenv import load_dotenv
# from google import genai

# load_dotenv()
# client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
# for m in client.models.list():
#     if "generateContent" in (m.supported_actions or []):
#         print(m.name)


#   For Groq:
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])
for m in client.models.list().data:
    print(m.id)