# Embedding model for the PDFs and the chat model (Groq by default, Gemini if set in .env)
import os
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

#   Embedding Model:
model = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")

#   Chat Model (set LLM_PROVIDER=gemini in .env to use Gemini):
if os.getenv("LLM_PROVIDER", "groq").lower() == "gemini":
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"), temperature=0)
else:
    from langchain_groq import ChatGroq
    llm = ChatGroq(model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"), temperature=0)

#   BACKUP MODELS:
#1. gemini-3.1-flash-lite
#2. gemini-3.5-flash
#3. openai/gpt-oss-20b
#4. qwen/qwen3.8-27b
