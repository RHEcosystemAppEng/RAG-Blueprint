import os
from sentence_transformers import SentenceTransformer
from langchain_postgres import PGVector
import pandas as pd
import pdfplumber

# Env vars
minio_endpoint = os.getenv('MINIO_ENDPOINT')
minio_access_key = os.getenv('MINIO_ACCESS_KEY')
minio_secret_key = os.getenv('MINIO_SECRET_KEY')
pg_connection = os.getenv('PG_CONNECTION')
embedding_model_name = os.getenv('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2')

# Extract from PDf
def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
        return text

model = SentenceTransformer(embedding_model_name)

vector_store = PGVector(
    embeddings=model,
    collection_name="document_embeddings",
    connection=pg_connection,
    use_jsonb=True
)

if input_file.endswith('.pdf'):
    text = extract_text_from_pdf(input_file)
    texts = text.split("\n")  # Chunk by line, you can adjust this logic

else:
    chunk_size = 1000
    result = []
    for chunk in pd.read_csv(input_file, chunksize=chunk_size):
        texts = chunk.astype(str).agg(" ".join, axis=1).tolist()
        embeddings = model.encode(texts)

        for txt, emb in zip(texts, embeddings):
            result.append({"text": txt, "embedding": emb.tolist()})

    vector_store.add_documents(result)

print(f"Processed and stored embeddings successfully.")
