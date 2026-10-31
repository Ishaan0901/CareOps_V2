# Run once (python AI/phase_1.py): reads the PDFs and builds the FAISS index in Vector_Store
from pathlib import Path
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from models import model
from dotenv import load_dotenv
load_dotenv()
ROOT = Path(__file__).resolve().parent.parent


#   Document Loaders:
docs=PyPDFDirectoryLoader(str(ROOT / 'data' / 'RAG_Pdfs')).load()



#   Text Splitters:
splitter=RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=200
)
chunks=splitter.split_documents(docs)



#   VectorStore:
FAISS.from_documents(
    embedding=model,
    documents=chunks
).save_local(str(ROOT / 'Vector_Store'))