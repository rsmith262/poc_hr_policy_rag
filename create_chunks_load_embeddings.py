from azure.storage.blob import BlobServiceClient
import fitz  # PyMuPDF
import io
import re
from pinecone import Pinecone

from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os

##########################################################

openai_api = os.getenv("OPENAI_API_KEY")

##########################################################
# Azure Blob Storage connection details
connection_string = os.getenv("BLOB_STORAGE_CONNECTION_STRING")
container_name = os.getenv("BLOB_STORAGE_CONTAINER")
storage_account_name = os.getenv("BLOB_STORAGE_ACCOUNT")

blob_service_client = BlobServiceClient.from_connection_string(connection_string)
container_client = blob_service_client.get_container_client(container_name)

def read_blob_to_bytes(blob_name):
    blob_client = container_client.get_blob_client(blob_name)
    blob_data = blob_client.download_blob().readall()
    return io.BytesIO(blob_data)

##########################################################
# Chunking logic

# converts the headings to markdown so it can be used for chnunking
def convert_to_markdown_style(text):
    text = re.sub(r"\n(\d+\.\s+[A-Z][^\n]+)", r"\n## \1", text)  # numbered headings
    text = re.sub(r"\n([A-Z][A-Za-z\s]+)\n", r"\n## \1\n", text)   # capitalized headers
    return text

# extracts page data first with metadata including page number blob name and url
def extract_text_by_page(blob_data, blob_name):
    doc = fitz.open(stream=blob_data, filetype="pdf")
    page_texts = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        text = re.sub(r"\n{2,}", "\n\n", text)
        text = re.sub(r"Page\s*\d+", "", text)
        text = re.sub(r"\s{2,}", " ", text)
        text = f"[Page {page_num}]\n\n{text}"
        metadata = {
            "page_number": page_num,
            "document": blob_name,
            "source": f"https://{storage_account_name}.blob.core.windows.net/{container_name}/{blob_name}"
        }
        page_texts.append({"text": text.strip(), "metadata": metadata})
    return page_texts

# then splits further on markdown sections retianing the page metadata
def split_by_headings_within_pages(page_texts):
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[("##", "section")])
    all_sections = []
    for page in page_texts:
        markdown_text = convert_to_markdown_style(page["text"])
        structured_docs = splitter.split_text(markdown_text)
        for doc in structured_docs:
            doc.metadata.update(page["metadata"])
            all_sections.append(doc)
    return all_sections

# creates chunks with overlap using the sections from the previous function
def chunk_sections_with_metadata(docs, chunk_size=1000, chunk_overlap=200):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    all_chunks = []
    for doc in docs:
        base_metadata = doc.metadata.copy()
        section_name = base_metadata.get("section") or "Unknown"
        chunks = splitter.split_text(doc.page_content)
        for i, chunk in enumerate(chunks):
            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["source_section"] = section_name
            all_chunks.append({"content": chunk, "metadata": chunk_metadata})
    return all_chunks

##########################################################
# generate embeddings from chunks

model_name = 'text-embedding-ada-002'

embed = OpenAIEmbeddings(
    model=model_name,
    api_key=openai_api
)

def generate_embeddings(chunked_docs):
    text_chunks = [chunk["content"] for chunk in chunked_docs]
    embeddings = embed.embed_documents(text_chunks)
    return embeddings

##########################################################
# Store in Pinecone

pc_api_key = os.getenv("PINECONE_API_KEY")
pc_index = os.getenv("PINECONE_INDEX")

pc = Pinecone(api_key=pc_api_key)
index = pc.Index(pc_index)

# stores embeddings in pinecone
def store_embeddings_in_pinecone(embeddings, chunked_docs, document_name):
    pinecone_vectors = []
    for i, (embedding, chunk_dict) in enumerate(zip(embeddings, chunked_docs)):
        metadata = chunk_dict["metadata"]
        metadata["chunk_id"] = f"{document_name}_p{metadata.get('page_number', 'X')}_c{metadata['chunk_index']}"
        metadata["text"] = chunk_dict["content"]
        pinecone_vectors.append((metadata["chunk_id"], embedding, metadata))
    index.upsert(vectors=pinecone_vectors)

##########################################################
# Run pipeline

blob_data = list(container_client.list_blobs())
blob_list = [blob.name for blob in blob_data]

for name in blob_list:
    blob_data = read_blob_to_bytes(name)
    page_texts = extract_text_by_page(blob_data, name)
    section_docs = split_by_headings_within_pages(page_texts)
    chunked_docs = chunk_sections_with_metadata(section_docs)
    embeddings = generate_embeddings(chunked_docs)
    store_embeddings_in_pinecone(embeddings, chunked_docs, name)