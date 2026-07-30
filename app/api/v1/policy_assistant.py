from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import RAGService

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
