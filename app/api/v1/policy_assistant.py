import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status
from fastapi.responses import StreamingResponse
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse, FeedbackRequest, FeedbackResponse
from app.services.rag_service import RAGService, POLICIES_DIR

router = APIRouter(prefix="/policy-assistant", tags=["AI Policy Assistant (RAG)"])


@router.post("/query", response_model=RAGQueryResponse)
def query_policy_assistant(payload: RAGQueryRequest):
    """
    RAG-powered AI Assistant for company policy questions.
    Answers user queries grounded strictly in provided policy documents with citations.
    """
    rag = RAGService.get_instance()
    return rag.query_policy(
        query=payload.query,
        document_filter=payload.document_filter,
        history=payload.history
    )


@router.post("/upload-document")
async def upload_policy_document(file: UploadFile = File(...)):
    """
    Upload a new custom PDF or Markdown policy document to the knowledge base.
    The document will be instantly indexed and used to answer user questions.
    """
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".md")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF (.pdf) and Markdown (.md) policy files are supported."
        )

    os.makedirs(POLICIES_DIR, exist_ok=True)
    destination_path = os.path.join(POLICIES_DIR, file.filename)

    with open(destination_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    rag = RAGService.get_instance()
    rag.load_and_index_documents(force_reindex=False)

    return {
        "status": "success",
        "message": f"Successfully uploaded and indexed policy document '{file.filename}'",
        "filename": file.filename
    }


@router.post("/stream")
async def stream_policy_query(payload: RAGQueryRequest):
    """
    Streaming RAG assistant endpoint (Server-Sent Events / token streaming).
    """
    rag = RAGService.get_instance()
    return StreamingResponse(
        rag.stream_policy_query(query=payload.query, document_filter=payload.document_filter),
        media_type="text/event-stream"
    )


@router.get("/documents")
def list_indexed_policy_documents():
    """Returns metadata about all indexed policy documents and sections."""
    rag = RAGService.get_instance()
    docs = {}
    for chunk in rag.chunks:
        if chunk.doc_name not in docs:
            docs[chunk.doc_name] = []
        docs[chunk.doc_name].append(chunk.section_title)

    return {
        "indexed_documents_count": len(docs),
        "total_sections": len(rag.chunks),
        "documents": [
            {"document_name": doc_name, "sections": list(set(sections))}
            for doc_name, sections in docs.items()
        ]
    }


@router.post("/feedback", response_model=FeedbackResponse)
def submit_rag_feedback(payload: FeedbackRequest):
    """Submits user rating (1-5 stars) and comments for RAG answer quality."""
    rag = RAGService.get_instance()
    return rag.record_feedback(payload)
