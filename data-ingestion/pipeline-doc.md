
# Kubeflow Pipeline for Document Processing and Embedding Storage

This repository provides a Kubeflow pipeline that automates the process of fetching documents from **MinIO**, chunking them, generating embeddings using a transformer model, and storing the embeddings in a **PostgreSQL** database (with PGVector extension). The pipeline is designed to handle both **CSV** and **PDF** documents.

## Overview

This pipeline consists of two main components:
1. **Fetching Data from MinIO**: Retrieves a document from a MinIO bucket.
2. **Chunking and Embedding**: Processes the document (CSV or PDF), generates embeddings using a pre-trained model (SentenceTransformer), and stores the embeddings in a PostgreSQL database with the PGVector extension for efficient vector search.

## Requirements

- **Kubeflow Pipelines**: For orchestrating the workflow.
- **MinIO**: S3-compatible storage for fetching documents.
- **Sentence-Transformers**: For generating document embeddings.
- **PostgreSQL with PGVector**: To store the embeddings for efficient vector search.

## Components

### 1. `fetch_from_minio`
This component is responsible for fetching documents from MinIO. It takes the following inputs:
- **`bucket_name`**: The name of the MinIO bucket.
- **`file_key`**: The path of the file within the MinIO bucket.
- **`minio_endpoint`**: The endpoint for MinIO.
- **`minio_access_key`** and **`minio_secret_key`**: Credentials for MinIO access.

The component downloads the file and outputs the file path for the next component to process.

### 2. `chunk_and_embed`
This component processes the fetched document. It can handle both **CSV** and **PDF** formats:
- **CSV**: The document is chunked by rows, and embeddings are generated for each row of text.
- **PDF**: The text is extracted from the PDF, chunked by lines, and embeddings are generated for each chunk.

It uses the **SentenceTransformer** model (`all-MiniLM-L6-v2`) to generate embeddings for the text. The embeddings are stored in a **PostgreSQL** database with the **PGVector** extension for efficient similarity search.

#### Inputs:
- **`input_file`**: The file path of the document (from the `fetch_from_minio` component).
- **`embeddings_output`**: The file path where the generated embeddings will be saved (this could be the PostgreSQL database in the future).

#### Outputs:
- **Embeddings JSON**: The generated embeddings are saved to the output path specified (`embeddings_output`).

## Pipeline Overview

1. **Fetch Data**: The pipeline fetches the document from a **MinIO** bucket.
2. **Process Data**: The document is chunked and embeddings are generated using a transformer model.
3. **Store Embeddings**: The embeddings are stored in a **PostgreSQL** database using the **PGVector** extension.

### Example Pipeline

```python
from kfp.dsl import pipeline, OutputPath, InputPath
from kfp.v2 import compiler

@pipeline(name="pipeline-fetch-chunk-embed")
def full_pipeline():
    # Fetch data from MinIO
    fetch_step = fetch_from_minio(
        bucket_name="llama",
        file_key="austinHousingData.csv",
        minio_endpoint="https://minio-api-minio.apps.ai-dev02.kni.syseng.devcluster.openshift.com",
        minio_access_key="minio",
        minio_secret_key="minio123"
    )

    # Specify the output path for embeddings
    embeddings_output = "/tmp/kfp_outputs/embeddings_output.json"  # Path for storing embeddings

    # Process data, chunk and embed it
    chunk_and_embed(
        input_file=fetch_step.outputs["output_file"],  # This is the input artifact
        embeddings_output=embeddings_output  # Pass the output path for embeddings
    )

# Compile the pipeline
compiler.Compiler().compile(
    pipeline_func=full_pipeline,
    package_path="fetch_chunk_embed_pipeline.yaml"
)
```

## How to Run

### Prerequisites:
- **Kubeflow Pipelines**: Make sure Kubeflow Pipelines is set up and running on your Kubernetes cluster.
- **MinIO**: Set up an S3-compatible MinIO service and make sure it’s accessible to the pipeline.
- **PostgreSQL with PGVector**: Deploy a PostgreSQL instance with the **PGVector** extension. If you don't have PGVector set up, follow the instructions [here](https://github.com/pgvector/pgvector).

### Running the Pipeline:
1. **Install the required dependencies** using `pip` (if you haven’t already):
   ```bash
   pip install boto3 pandas sentence-transformers pdfplumber minio
   ```

2. **Compile the pipeline**: 
   Use the compiler to generate the `.yaml` file for your pipeline.
   ```bash
   compiler.Compiler().compile(pipeline_func=full_pipeline, package_path="pipeline.yaml")
   ```

3. **Run the pipeline**: Upload the `.yaml` file to the Kubeflow Pipelines UI and run the pipeline.

### Environment Variables:
Make sure to set the following environment variables for accessing **MinIO** and **PostgreSQL**:

- **MINIO_ENDPOINT**: The endpoint URL for your MinIO service.
- **MINIO_ACCESS_KEY**: Your MinIO access key.
- **MINIO_SECRET_KEY**: Your MinIO secret key.
- **PG_CONNECTION**: The PostgreSQL connection string (`postgresql://username:password@host:port/database_name`).


## License
This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
