#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Pipeline with Docling, pgvector and vLLM

This script implements a Retrieval Augmented Generation (RAG) pipeline using:
- Docling for document processing
- pgvector for vector storage
- vLLM for LLM inference

Requirements:
    pip install git+https://github.com/ibm-granite-community/utils \
        transformers \
        langchain_community \
        langchain-huggingface \
        langchain-milvus \
        langchain_postgres \
        replicate \
        psycopg \
        wget
"""

import sys
import logging
from typing import List, Optional

# LangChain and Vector DB components
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_ollama import OllamaLLM
from langchain_community.llms.vllm import VLLM

# Docling imports
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.types.doc.labels import DocItemLabel

# Transformers for tokenization
from transformers import AutoTokenizer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class RAGPipeline:
    """RAG Pipeline implementation using Docling, pgvector, and vLLM."""

    def __init__(
        self,
        embeddings_model_path: str = "sentence-transformers/all-mpnet-base-v2",
        db_connection: str = "postgresql+psycopg://pgvector:pgvector@localhost:6024/pgvector",
        collection_name: str = "pgvector",
        llm_backend: str = "ollama",  # Either "ollama" or "vllm"
        ollama_model_name: str = "llama3",
        ollama_base_url: str = "http://localhost:11434",
        vllm_model_name: str = "meta-llama/Llama-3.2-3B-Instruct",
        vllm_server_url: str = "http://localhost:8000",
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ):
        """
        Initialize the RAG pipeline.

        Args:
            embeddings_model_path: Path to the embedding model
            db_connection: PostgreSQL connection string
            collection_name: Name of the vector collection in pgvector
            vllm_model_name: Model name as configured in vLLM server
            vllm_server_url: URL of the vLLM server
            max_new_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
        """
        self.embeddings_model_path = embeddings_model_path
        self.db_connection = db_connection
        self.collection_name = collection_name
        self.llm_backend = llm_backend.lower()
        self.ollama_model_name = ollama_model_name
        self.ollama_base_url = ollama_base_url
        self.vllm_model_name = vllm_model_name
        self.vllm_server_url = vllm_server_url
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        
        # Initialize components
        self._init_embeddings()
        self._init_vector_store()
        self._init_llm()
        self._init_rag_chain()
        
        # Document converter
        self.converter = DocumentConverter()
        
    def _init_embeddings(self):
        """Initialize the embeddings model."""
        logger.info(f"Initializing embeddings model: {self.embeddings_model_path}")
        self.embeddings_model = HuggingFaceEmbeddings(
            model_name=self.embeddings_model_path,
        )
        self.embeddings_tokenizer = AutoTokenizer.from_pretrained(self.embeddings_model_path)
        
    def _init_vector_store(self):
        """Initialize the vector store."""
        logger.info(f"Connecting to vector database at {self.db_connection}")
        self.vector_store = PGVector(
            embeddings=self.embeddings_model,
            collection_name=self.collection_name,
            connection=self.db_connection,
            use_jsonb=True,
        )
        
    def _init_llm(self):
        """Initialize the LLM connection based on selected backend."""
        if self.llm_backend == "ollama":
            logger.info(f"Connecting to Ollama server at {self.ollama_base_url} with model {self.ollama_model_name}")
            self.llm = OllamaLLM(
                model=self.ollama_model_name,
                base_url=self.ollama_base_url,
                stop=["Human:", "Assistant:"],
                num_ctx=2048,
                num_predict=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
            )
        elif self.llm_backend == "vllm":
            logger.info(f"Connecting to vLLM server at {self.vllm_server_url} with model {self.vllm_model_name}")
            self.llm = VLLM(
                model_name=self.vllm_model_name,
                server_url=self.vllm_server_url,
                stop_sequences=["Human:", "Assistant:"],
                max_new_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
            )
        else:
            raise ValueError(f"Unsupported LLM backend: {self.llm_backend}. Use 'ollama' or 'vllm'.")
        
    def _init_rag_chain(self):
        """Initialize the RAG chain."""
        # Create a prompt template for question-answering
        prompt_template = PromptTemplate.from_template(
            """
            You are a helpful assistant that answers questions based on the provided context.
            
            Context:
            {context}
            
            Question: {input}
            
            Answer the question using only the information provided in the context. 
            If the information is not in the context, say "I don't have enough information to answer this question."
            """
        )
        
        # Document prompt template to format each retrieved document
        document_prompt = PromptTemplate.from_template("Document {doc_id}:\n{page_content}")
        document_separator = "\n\n"
        
        # Create the document chain
        combine_docs_chain = create_stuff_documents_chain(
            llm=self.llm,
            prompt=prompt_template,
            document_prompt=document_prompt,
            document_separator=document_separator,
        )
        
        # Create the retriever
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 4})
        
        # Create the full RAG chain
        self.rag_chain = create_retrieval_chain(
            retriever=self.retriever,
            combine_docs_chain=combine_docs_chain,
        )
        
    def process_documents(self, sources: List[str]) -> List[str]:
        """
        Process documents from sources, chunk them, and add to vector store.
        
        Args:
            sources: List of document sources (URLs or file paths)
            
        Returns:
            List of document IDs added to the vector store
        """
        logger.info(f"Processing {len(sources)} documents")
        
        # Convert and chunk documents
        i = 0
        texts: List[Document] = []
        
        for source in sources:
            logger.info(f"Converting document from source: {source}")
            try:
                doc = self.converter.convert(source=source).document
                chunks = HybridChunker(tokenizer=self.embeddings_tokenizer).chunk(doc)
                
                for chunk in chunks:
                    if any(filter(lambda c: c.label in [DocItemLabel.TEXT, DocItemLabel.PARAGRAPH], 
                                 iter(chunk.meta.doc_items))):
                        i += 1
                        texts.append(Document(
                            page_content=chunk.text, 
                            metadata={"doc_id": i, "source": source}
                        ))
            except Exception as e:
                logger.error(f"Error processing document {source}: {str(e)}")
        
        logger.info(f"Created {len(texts)} document chunks")
        
        # Add documents to vector store
        if texts:
            ids = self.vector_store.add_documents(texts)
            logger.info(f"Added {len(ids)} documents to vector store")
            return ids
        else:
            logger.warning("No valid document chunks were created")
            return []
    
    def query(self, question: str) -> dict:
        """
        Query the RAG pipeline with a question.
        
        Args:
            question: The question to answer
            
        Returns:
            Dictionary containing the answer and retrieved context
        """
        logger.info(f"Querying RAG pipeline: {question}")
        result = self.rag_chain.invoke({"input": question})
        
        # Log retrieved documents
        logger.info(f"Retrieved {len(result['context'])} documents")
        for i, doc in enumerate(result["context"]):
            logger.debug(f"Document {i+1} (source: {doc.metadata['source']}): "
                        f"{doc.page_content[:150]}...")
        
        return result
    
    def test_llm(self, prompt: str) -> str:
        """
        Test the LLM connection with a simple prompt.
        
        Args:
            prompt: Test prompt
            
        Returns:
            LLM response
        """
        logger.info("Testing LLM connection")
        return self.llm.invoke(prompt)
    
    def get_retriever(self):
        """
        Get the retriever instance for direct retrieval testing.
        
        Returns:
            Configured retriever
        """
        return self.retriever


def main():
    """Main function to demonstrate the RAG pipeline."""
    import argparse
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(description="RAG Pipeline with Docling, pgvector, and LLM backend")
    parser.add_argument("--backend", type=str, choices=["ollama", "vllm"], default="ollama",
                      help="LLM backend to use (ollama or vllm)")
    parser.add_argument("--model", type=str, default=None,
                      help="Model name to use with the selected backend")
    parser.add_argument("--server-url", type=str, default=None,
                      help="Server URL for the selected backend")
    args = parser.parse_args()
    
    # Example sources
    sources = [
        "https://www.ufc.com/news/main-card-results-highlights-winner-interviews-ufc-310-pantoja-vs-asakura",
        "https://media.ufc.tv/discover-ufc/Unified_Rules_MMA.pdf",
    ]
    
    # Initialize the RAG pipeline
    try:
        # Set up parameters based on selected backend
        kwargs = {
            "llm_backend": args.backend,
        }
        
        # Add backend-specific parameters if provided
        if args.backend == "ollama":
            if args.model:
                kwargs["ollama_model_name"] = args.model
            if args.server_url:
                kwargs["ollama_base_url"] = args.server_url
        elif args.backend == "vllm":
            if args.model:
                kwargs["vllm_model_name"] = args.model
            if args.server_url:
                kwargs["vllm_server_url"] = args.server_url
                
        # Initialize the pipeline with selected parameters
        rag_pipeline = RAGPipeline(**kwargs)
        
        # Test LLM connection
        test_response = rag_pipeline.test_llm("Tell me briefly what you know about UFC fights.")
        print("LLM test response:")
        print(test_response)
        print("-" * 80)
        
        # Process documents
        rag_pipeline.process_documents(sources)
        
        # Test retrieval directly
        retriever = rag_pipeline.get_retriever()
        docs = retriever.invoke("Who won in the Pantoja vs Asakura fight at UFC 310?")
        print(f"Retrieved {len(docs)} documents")
        
        # Test the full RAG pipeline
        question = "Who won in the Pantoja vs Asakura fight at UFC 310?"
        result = rag_pipeline.query(question)
        
        print("Retrieved documents:")
        for i, doc in enumerate(result["context"]):
            print(f"Document {i+1} (source: {doc.metadata['source']}):")
            print(doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content)
            print()
        
        print("RAG response:")
        print(result["answer"])
        
    except Exception as e:
        logger.error(f"Error in RAG pipeline: {str(e)}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())