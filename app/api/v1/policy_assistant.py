import os
import shutil
import math
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
async def upload_policy_documents(files: List[UploadFile] = File(...)):
    """
    Upload one or multiple custom policy documents (PDF, TXT, MD, CSV) to the Grounding Library.
    The documents will be instantly indexed and used to answer user questions.
    """
    os.makedirs(POLICIES_DIR, exist_ok=True)
    uploaded = []

    for file in files:
        destination_path = os.path.join(POLICIES_DIR, file.filename)
        with open(destination_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        uploaded.append(file.filename)

    rag = RAGService.get_instance()
    rag.load_and_index_documents(force_reindex=False)

    return {
        "status": "success",
        "message": f"Successfully uploaded and indexed {len(uploaded)} document(s).",
        "filenames": uploaded
    }


@router.delete("/documents/{filename}")
def delete_indexed_document(filename: str):
    """Deletes an indexed document from Grounding Library."""
    rag = RAGService.get_instance()
    success = rag.delete_document(filename)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{filename}' not found."
        )
    return {"status": "success", "message": f"Deleted document '{filename}'."}


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

    documents_metadata = []
    if os.path.exists(POLICIES_DIR):
        for filename in os.listdir(POLICIES_DIR):
            filepath = os.path.join(POLICIES_DIR, filename)
            size_kb = round(os.path.getsize(filepath) / 1024, 1)
            doc_title = filename.replace(".pdf", "").replace(".md", "").replace(".txt", "").replace("_", " ").title()
            chunks_count = sum(1 for c in rag.chunks if c.file_path == filepath)
            documents_metadata.append({
                "filename": filename,
                "document_name": doc_title,
                "size": f"{size_kb} KB",
                "chunks": f"{chunks_count} nodes",
                "pages": f"{max(1, math.ceil(chunks_count / 2))} pg",
                "status": "Indexed"
            })

    return {
        "indexed_documents_count": len(documents_metadata),
        "total_sections": len(rag.chunks),
        "documents": documents_metadata
    }


@router.post("/feedback", response_model=FeedbackResponse)
def submit_rag_feedback(payload: FeedbackRequest):
    """Submits user rating (1-5 stars) and comments for RAG answer quality."""
    rag = RAGService.get_instance()
    return rag.record_feedback(payload)
