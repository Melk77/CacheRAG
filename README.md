# CacheRAG

CacheRAG is a document question-answering application built with
Retrieval-Augmented Generation (RAG). Users can upload documents to a
collection and ask questions about their contents. The backend retrieves
relevant document chunks, reranks them, and uses a language model to
generate answers with supporting sources.

CacheRAG also uses Redis to reduce repeated work through exact and
semantic answer caching.

## Features

-   **Document-based question answering:** Ask questions using the
    content of an uploaded document collection.
-   **Document processing:** Extract text from supported PDF and TXT
    documents, split text into chunks, and retain document metadata.
-   **Vector storage and retrieval:** Generate embeddings and store
    document vectors in Qdrant.
-   **Hybrid retrieval:** Combine retrieval methods to find relevant
    document chunks.
-   **Reranking:** Rerank retrieved chunks before sending context to the
    language model.
-   **Grounded responses:** Generate answers using retrieved document
    context and return available source references.
-   **Exact answer caching:** Use Redis to return a previously generated
    answer for the same normalized question and collection state.
-   **Semantic answer caching:** Use question embeddings and Qdrant
    similarity search to find reusable answers to sufficiently similar
    questions.
-   **Cache expiration and invalidation:** Apply TTL to Redis entries
    and invalidate cached answers when the underlying collection
    changes.
-   **Redis fallback:** Continue the normal RAG flow when Redis is
    unavailable instead of making caching a requirement for answering.
-   **Cache management:** Provide endpoints for cache statistics and
    manual answer-cache clearing.
-   **Performance metrics:** Track timings for cache lookup and the main
    RAG stages.

## Technology Stack

  Layer                 Technology
  --------------------- --------------------------------------------
  Frontend              React, Vite
  Backend API           Python, FastAPI
  Relational database   PostgreSQL, SQLAlchemy
  Vector database       Qdrant
  Answer cache          Redis
  Embeddings            Sentence Transformers (`all-MiniLM-L6-v2`)
  Language model        Groq API

## Architecture Overview

``` text
User
  |
  v
React + Vite frontend
  |
  v
FastAPI backend
  |
  +--> Collection and document management
  |
  +--> Redis exact answer-cache lookup
  |       |
  |       +--> Exact hit: return cached answer and sources
  |
  +--> Semantic-cache lookup (Qdrant)
  |       |
  |       +--> Valid semantic hit: return cached answer
  |
  +--> RAG pipeline on cache miss
          |
          +--> Create question embedding
          +--> Hybrid document retrieval from Qdrant
          +--> Rerank retrieved chunks
          +--> Generate grounded answer with Groq
          +--> Save successful answer in Redis
          +--> Save semantic-cache reference in Qdrant

PostgreSQL: application and collection metadata
Qdrant: document vectors and semantic-cache vectors
Redis: cached answers with expiration
```

## Project Structure

The repository is organized into separate backend and frontend
applications:

``` text
CacheRAG/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── requirements.txt
│   └── ...
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
├── Caching_Summary.md
└── README.md
```

The exact contents may evolve as the project develops.

## Prerequisites

Install or prepare the following before running the application:

-   Python 3.11 or a compatible Python version supported by the backend
    dependencies
-   Node.js and npm
-   PostgreSQL
-   Redis
-   Qdrant
-   A Groq API key

Make sure PostgreSQL, Redis, and Qdrant are running and accessible to
the backend.

## Configuration

1.  Open the `backend` directory.
2.  Create a local `.env` file using the project's environment-variable
    example, if provided.
3.  Set the database connection, Redis connection, Qdrant connection,
    and Groq API configuration required by the backend settings.
4.  Keep credentials and API keys private. Do not commit `.env` files or
    production secrets to GitHub.

Check the backend configuration module and environment example in the
repository for the exact variable names required by your version.

## Run the Backend

From the project root, open PowerShell:

``` powershell
cd backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

uvicorn app.main:app --reload
```

The API documentation is available at:

``` text
http://127.0.0.1:8000/docs
```

If PowerShell blocks virtual-environment activation, use the
execution-policy instructions appropriate for your machine or activate
the environment through your IDE.

## Run the Frontend

Open a second terminal:

``` powershell
cd frontend

npm install
npm run dev
```

Open the local URL printed by Vite in the terminal.

For a production build:

``` powershell
npm run build
```

## Caching Design

CacheRAG uses a cache-aside approach:

1.  The backend builds an exact cache key using the collection ID,
    collection version, normalized question, and web-search mode.
2.  Redis is checked before the expensive RAG operations.
3.  If there is no exact hit, CacheRAG checks the semantic cache using
    the question embedding and the matching
    collection/version/web-search scope.
4.  A semantic result is reused only when it meets the similarity
    threshold and its answer is still present in Redis.
5.  If neither cache returns a valid answer, the backend retrieves and
    reranks document chunks, generates an answer, and attempts to cache
    the successful result.

### TTL and invalidation

Redis entries expire according to the configured TTL.
Collection-version-aware cache keys and collection cache invalidation
help prevent answers based on old document content from being reused
after collection changes.

### Eviction policy

The production Redis configuration uses a bounded memory limit with the
`allkeys-lru` eviction policy. LRU, LFU, random eviction, and a separate
FIFO simulation were explored. See
[Caching_Summary.md](Caching_Summary.md) for the design, trade-offs,
experiment notes, and remaining evaluation evidence.

### Redis failure behavior

Caching is an optimization rather than a hard dependency. If a Redis
read fails, the request proceeds as a cache miss and continues through
the RAG pipeline. If a Redis write fails, the generated answer can still
be returned even though it was not cached. Semantic-cache references are
not deleted solely because Redis is unreachable.

## Cache Management API

The backend provides cache-management endpoints:

  Method     Endpoint           Purpose
  ---------- ------------------ ---------------------------
  `GET`      `/cache/stats`     Retrieve cache statistics
  `DELETE`   `/cache/answers`   Clear cached answers

For the complete interactive API specification, start the backend and
visit `/docs`.

## Evaluation and Demo Checklist

Use the following scenarios when demonstrating the system:

1.  **Cache miss:** Ask a new question and verify that document
    retrieval, reranking, and answer generation run.
2.  **Exact cache hit:** Ask the same question again and verify that the
    cached answer is returned without repeating the RAG pipeline.
3.  **Semantic cache hit:** Ask a sufficiently similar question and
    verify that a valid semantic match is reused.
4.  **TTL expiration:** Verify that an expired Redis answer is not
    reused.
5.  **Collection invalidation:** Update or delete collection documents
    and verify that old cached answers cannot be served.
6.  **Redis unavailable:** Verify that the application continues
    answering through the normal RAG path when Redis cannot be reached.
7.  **Eviction behavior:** Explain the LRU, LFU, FIFO, and random-policy
    comparison and its experimental limitations.
8.  **Performance:** Compare cached and uncached response times and
    report available cache, retrieval, reranking, and LLM timing
    metrics.

Do not report a scenario as verified until its result has been captured.

## Documentation

-   [Caching Summary](Caching_Summary.md) --- one-page overview of cache
    patterns, TTL, invalidation, eviction policies, Redis failure
    handling, and evaluation evidence.

## Security and Git Hygiene

Before publishing or sharing the repository:

-   Keep `.env` files, API keys, passwords, and tokens out of Git.
-   Do not commit `.venv/`, `node_modules/`, Python cache files,
    generated build output, or local database/storage files unless
    intentionally required.
-   Commit an environment-variable example with placeholder values
    rather than real credentials.
-   Review staged changes before committing:

``` powershell
git status
git diff --cached
```

## Project Status

CacheRAG has implemented the core document-processing, RAG,
retrieval/reranking, and caching workflows. Some mentor-evaluation
evidence---such as complete frontend cache demonstrations, a real Redis
network-outage check, and final performance charts---must be captured
before claiming that every evaluation criterion has been completed.

------------------------------------------------------------------------

**CacheRAG** --- Ask questions about your documents, retrieve relevant
evidence, and reuse answers efficiently.
