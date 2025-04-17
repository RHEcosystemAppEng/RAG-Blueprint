import uuid
from llama_stack_client import LlamaStackClient
from llama_stack_client.types import Document as LlamaStackDocument

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.types.doc.labels import DocItemLabel

# === Step 1: Configure Llama Stack client ===
client = LlamaStackClient(base_url="http://localhost:8321")  # Assumes LLAMA_STACK_API_KEY is set in env

# === Step 2: Define local input files (PDFs or .md) ===
local_files = [
    "docling.pdf",
]

# === Step 3: Convert, Chunk, and Prepare Documents ===

# converter format option for the pictures on pdf to be generated as base64
pipeline_options = PdfPipelineOptions()
pipeline_options.generate_picture_images = True
converter = DocumentConverter(
            format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
)
chunker = HybridChunker()
documents: list[LlamaStackDocument] = []
i = 0

for file_path in local_files:
    print(f"Processing {file_path}...")
    try:
        docling_doc = converter.convert(source=file_path).document
        chunks = chunker.chunk(docling_doc)

        for chunk in chunks:
            if any(
                c.label in [DocItemLabel.TEXT, DocItemLabel.PARAGRAPH]
                for c in chunk.meta.doc_items
            ):
                i += 1
                documents.append(
                    LlamaStackDocument(
                        document_id=f"doc-{i}",
                        content=chunk.text,
                        mime_type="text/plain",
                        metadata={"source": file_path},
                    )
                )
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

print(f"Total valid documents prepared: {len(documents)}")

# === Step 4: Create Vector DB ===
# vector_providers = [
#     provider for provider in client.providers.list() if provider.api == "vector_io"
# ]
# selected_vector_provider = vector_providers[1]
vector_db_id = "pgvector1" #f"test_vector_db_{uuid.uuid4()}"

try:
    client.vector_dbs.register(
        vector_db_id= vector_db_id,
        embedding_model="all-MiniLM-L6-v2",
        embedding_dimension=384,
        provider_id= "pgvector", #selected_vector_provider.provider_id,
    )
    print(f"Vector DB registered successfully: {vector_db_id}")

except Exception as e:
    print(f"Failed to register vector DB '{vector_db_id}': {e}")


print(f"Vector DB registered: {vector_db_id}")

# === Step 5: Insert into Vector DB ===
try:
    client.tool_runtime.rag_tool.insert(
        documents=documents,
        vector_db_id=vector_db_id,
        chunk_size_in_tokens=512,
    )
    print("Documents successfully inserted into the vector DB.")

except Exception as e:
    print(f"Error inserting documents into RAG tool: {e}")


print("Documents successfully inserted into RAG tool.")
