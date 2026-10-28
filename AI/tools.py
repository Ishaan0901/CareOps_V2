"""RAG tool: searches the hospital PDFs (FAISS vector store) and returns text with source file names."""
import os
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from models import model
from dotenv import load_dotenv
load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

#   Retriever:
store = FAISS.load_local(
    str(ROOT / "Vector_Store"),
    embeddings=model,
    allow_dangerous_deserialization=True
)

retriever = store.as_retriever(search_kwargs={"k": 8})



#   Search_hospital_docs:
@tool
def Search_hospital_docs(question:str):

    '''
    Search the hospital knowledge base (policies, SOPs and guides) and return the most relevant text passages with their source file names.

    Use this tool for questions about hospital rules and procedures, such as overcrowding and surge levels, triage, bed management and discharge, staffing ratios and shifts, infection control, biomedical waste, equipment and support services, ICU and operating theatre operations, fees, billing and insurance, visiting hours, emergency codes and patient safety.

    Input: question must be a complete, standalone question that makes sense without the chat history. For example, write "What is the nurse to patient ratio in the emergency department?" and not "And in the emergency department?".
    '''

    #   Fetch the useful docs using retriever:
    docs = retriever.invoke(question)

    #   Convert docs into one string (with source file name):
    context = "\n\n".join(
        f"[Source: {os.path.basename(d.metadata.get('source', 'unknown'))}]\n{d.page_content}"
        for d in docs
    )

    #   Return the context
    return context
