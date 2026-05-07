# Smart Contract Assistant

A local RAG application for uploading contract documents, asking clause-specific questions, and generating citation-backed summaries through a Gradio interface and FastAPI backend.

The project is designed for contract review workflows where users need quick answers about payment terms, termination clauses, obligations, risk areas, dates, penalties, and other agreement details.

## Demo Video

[Watch the project recording](./Recording.mp4)

## Features

- Upload and index one or more `.pdf` or `.docx` contract files.
- Ask questions against the indexed contract content.
- Generate executive summaries focused on parties, obligations, payment terms, duration, termination, and risk clauses.
- Return source citations from retrieved document pages or sections.
- Preview uploaded PDF documents in the UI.
- Export chat history and download generated summaries.
- Run fully locally with Ollama, ChromaDB, LangChain, FastAPI, and Gradio.

## Tech Stack

- **Frontend:** Gradio
- **Backend:** FastAPI
- **RAG framework:** LangChain
- **LLM provider:** Ollama
- **Vector database:** ChromaDB
- **Embeddings:** Sentence Transformers, with deterministic fake embeddings fallback
- **Document parsing:** PyMuPDF for PDF, python-docx for DOCX

## Project Structure

```text
.
+-- app/
|   +-- api/
|   |   +-- server.py          # FastAPI app and API endpoints
|   +-- core/
|   |   +-- ingestion.py       # PDF/DOCX loading, chunking, and Chroma indexing
|   |   +-- rag_chain.py       # RAG service, prompts, retrieval, and summaries
|   +-- ui/
|       +-- interface.py       # Gradio user interface
+-- uploads/                   # Uploaded contract files
+-- chroma_db/                 # Persisted Chroma vector store
+-- main.py                    # FastAPI app entrypoint
+-- requirements.txt
+-- README.md
```

## Requirements

- Python 3.10+
- Ollama installed and running
- An Ollama chat model available locally, such as `llama3.2`

Install Ollama from:

```text
https://ollama.com
```

Pull the default model:

```powershell
ollama pull llama3.2
```

Start Ollama if it is not already running:

```powershell
ollama serve
```

## Installation

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Running the Application

Run the FastAPI backend:

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, run the Gradio UI:

```powershell
python -m app.ui.interface
```

Open the UI:

```text
http://127.0.0.1:7860
```

API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Usage

1. Start Ollama.
2. Start the FastAPI backend.
3. Start the Gradio interface.
4. Upload one or more PDF or DOCX contract files.
5. Click **Upload and Index**.
6. Ask contract-specific questions in the chat.
7. Use quick actions such as **Payment Terms**, **Termination Clause**, **Risky Clauses**, or **Summarize Contract**.

Example questions:

```text
What are the payment terms and due dates?
Explain the termination clause and notice period.
Are there any risky or one-sided clauses?
What penalties apply for late payment?
Who are the parties and what are their obligations?
```

## API Endpoints

### Health Check

```http
GET /health
```

Returns API status and whether the RAG services have been initialized.

### Upload Contracts

```http
POST /upload
```

Accepts one or more `.pdf` or `.docx` files, stores them in `uploads/`, clears the previous Chroma collection, indexes the new documents, and refreshes the retriever.

### Ask a Question

```http
POST /ask
```

Request body:

```json
{
  "question": "What does the contract say about termination?"
}
```

Returns:

```json
{
  "answer": "The generated answer...",
  "citations": [
    {
      "source": "contract.pdf",
      "section": "Page 3"
    }
  ]
}
```

### Generate Summary

```http
POST /summary
```

Generates a high-level summary of the indexed contract set.

## Configuration

The application can be configured with environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `API_BASE_URL` | `http://127.0.0.1:8000` | Backend URL used by the Gradio UI |
| `UPLOAD_DIR` | `./uploads` | Directory where uploaded files are stored |
| `CHROMA_PATH` | `./chroma_db` | ChromaDB persistence directory |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2:latest` | Chat model used for contract QA |
| `USE_FAKE_EMBEDDINGS` | `0` | Set to `1` to use deterministic fake embeddings for local testing |
| `ENABLE_LANGSERVE_ROUTES` | `0` | Set to `1` to expose optional LangServe routes |

Example:

```powershell
$env:OLLAMA_MODEL="llama3.2:latest"
$env:CHROMA_PATH="./chroma_db"
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## How It Works

1. Uploaded PDF and DOCX files are saved locally.
2. `DocumentProcessor` extracts text using PyMuPDF or python-docx.
3. Documents are split into chunks with overlap for better retrieval quality.
4. Chunks are embedded and stored in ChromaDB.
5. User questions are routed through a LangChain retrieval chain.
6. The LLM answers using only retrieved contract context.
7. The response includes citations based on source file and page or section metadata.

## Notes and Limitations

- The assistant is intended to support contract review, not replace legal advice.
- Answers depend on the quality of extracted text from the uploaded documents.
- Scanned PDFs without embedded text may require OCR before upload.
- Uploading a new contract set clears the previous indexed collection.
- The default model is local through Ollama; response quality depends on the installed model.

## Development

Run a syntax check:

```powershell
python -m py_compile app/ui/interface.py app/api/server.py app/core/ingestion.py app/core/rag_chain.py
```

Run the backend with reload during development:

```powershell
uvicorn main:app --reload
```

Run the frontend:

```powershell
python -m app.ui.interface
```

## License

Add your project license here.
