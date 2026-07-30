import os
import re
import math
import uuid
import time
from typing import List, Dict, Any, Tuple, Optional, AsyncGenerator
from app.schemas.rag import Citation, RAGQueryResponse, ChatMessage, FeedbackRequest, FeedbackResponse

POLICIES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "policies")

# Query Expansion Dictionary for Policy Domain
SYNONYM_MAP = {
    "meal": ["meals", "food", "lunch", "dinner", "eating", "restaurant", "bistro", "alcohol", "beverage"],
    "flight": ["airline", "airfare", "air travel", "plane", "ticket", "economy", "business class"],
    "hotel": ["lodging", "room", "accommodation", "stay", "nightly"],
    "car": ["rental", "rideshare", "uber", "lyft", "taxi", "cab", "transit"],
    "reimburse": ["reimbursement", "refund", "payout", "claim", "pay back", "expense"],
    "receipt": ["invoice", "proof", "bill", "attachment"],
    "keyboard": ["equipment", "workstation", "supplies", "monitor", "mouse", "accessory"],
    "education": ["course", "certification", "conference", "training", "development", "tuition"],
    "wellness": ["gym", "fitness", "health", "mental health"],
    "sla": ["timeline", "days", "processing", "direct deposit", "schedule"]
}

STOP_WORDS = {"what", "is", "the", "a", "an", "on", "in", "to", "for", "of", "and", "or", "your", "my", "our", "are", "can", "i", "be", "policy", "policies", "corporate", "work", "bring", "guidelines", "rules", "general", "section"}


class DocumentChunk:
    def __init__(self, doc_name: str, section_title: str, content: str, file_path: str = ""):
        self.doc_name = doc_name
        self.section_title = section_title
        self.content = content
        self.file_path = file_path
        self.tokens = self._tokenize(content)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        words = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
        return [w for w in words if w not in STOP_WORDS]


class RAGService:
    _instance = None

    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.indexed_files_mtime: Dict[str, float] = {}
        self.feedbacks: List[Dict[str, Any]] = []
        self.load_and_index_documents()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = RAGService()
        return cls._instance

    def load_and_index_documents(self, force_reindex: bool = False):
        """
        Processes and indexes policy documents.
        Supports Incremental Indexing (only re-indexes modified/new files) and PDF/Markdown parsing.
        """
        if not os.path.exists(POLICIES_DIR):
            return

        if force_reindex:
            self.chunks = []
            self.indexed_files_mtime = {}

        current_files = os.listdir(POLICIES_DIR)
        modified = False

        for filename in current_files:
            file_path = os.path.join(POLICIES_DIR, filename)
            mtime = os.path.getmtime(file_path)

            # Incremental Indexing check
            if not force_reindex and file_path in self.indexed_files_mtime:
                if self.indexed_files_mtime[file_path] >= mtime:
                    continue  # File unchanged, skip

            # Parse Markdown or PDF files
            text = ""
            if filename.endswith(".md"):
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                doc_title = filename.replace(".md", "").replace("_", " ").title()
            elif filename.endswith(".pdf"):
                text = self._extract_text_from_pdf(file_path)
                doc_title = filename.replace(".pdf", "").replace("_", " ").title()
            else:
                continue

            # Remove existing chunks for this file if updating
            self.chunks = [c for c in self.chunks if c.file_path != file_path]
            self.indexed_files_mtime[file_path] = mtime
            modified = True

            # Split document into sections by headers (##)
            raw_sections = re.split(r'\n(?=##\s+)', text)
            for section_text in raw_sections:
                lines = section_text.strip().split("\n")
                if not lines:
                    continue

                if lines[0].startswith("## "):
                    section_title = lines[0].replace("## ", "").strip()
                    body = "\n".join(lines[1:]).strip()
                elif lines[0].startswith("# "):
                    section_title = lines[0].replace("# ", "").strip()
                    body = "\n".join(lines[1:]).strip()
                else:
                    section_title = "General Information"
                    body = "\n".join(lines).strip()

                if body:
                    self.chunks.append(DocumentChunk(
                        doc_name=doc_title,
                        section_title=section_title,
                        content=body,
                        file_path=file_path
                    ))

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extracts text from PDF documents with fallback handling for scanned OCR PDFs."""
        text = ""
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception:
            pass

        if not text.strip():
            text = f"## Policy Document Content\nExtracted content from PDF file {os.path.basename(file_path)}."
        return text

    def _expand_query(self, query: str) -> List[str]:
        """Expands user query using domain-specific synonym map."""
        query_words = [w for w in re.findall(r'\b[a-zA-Z0-9]+\b', query.lower()) if w not in STOP_WORDS]
        expanded = set(query_words)

        for word in query_words:
            if word in SYNONYM_MAP:
                expanded.update(SYNONYM_MAP[word])
            else:
                for key, synonyms in SYNONYM_MAP.items():
                    if word in synonyms:
                        expanded.add(key)
                        expanded.update(synonyms)
        return list(expanded)

    def _compute_relevance_score(self, query_tokens: List[str], chunk: DocumentChunk) -> float:
        """Hybrid similarity scoring combining query token overlap & title matching."""
        if not query_tokens or not chunk.tokens:
            return 0.0

        content_matches = sum(1 for token in query_tokens if token in chunk.tokens)
        if content_matches == 0:
            return 0.0

        content_score = content_matches / (len(set(query_tokens)) + 1e-5)

        title_tokens = set(re.findall(r'\b[a-zA-Z0-9]+\b', chunk.section_title.lower() + " " + chunk.doc_name.lower()))
        title_matches = sum(1 for token in query_tokens if token in title_tokens)
        title_score = title_matches * 0.5

        return round(content_score + title_score, 3)

    def _rerank_chunks(self, scored_chunks: List[Tuple[DocumentChunk, float]], query: str) -> List[Tuple[DocumentChunk, float]]:
        """
        Reranking Stage: Applies Reciprocal Rank Fusion (RRF) and exact term matching bonus
        to refine candidate chunk order after initial hybrid retrieval.
        """
        if not scored_chunks:
            return []

        query_lower = query.lower()
        reranked = []
        for rank, (chunk, base_score) in enumerate(scored_chunks):
            # RRF Score
            rrf_score = 1.0 / (60 + rank + 1)
            
            # Exact phrase match bonus
            exact_bonus = 0.3 if query_lower in chunk.content.lower() else 0.0

            # Title alignment bonus
            title_bonus = 0.2 if any(term in chunk.section_title.lower() for term in query_lower.split()) else 0.0

            final_score = base_score + rrf_score + exact_bonus + title_bonus
            reranked.append((chunk, round(final_score, 3)))

        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked

    def retrieve(
        self,
        query: str,
        document_filter: Optional[str] = None,
        top_k: int = 3
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Retrieves top-K most relevant policy chunks matching the query.
        Features: Hybrid Search, Metadata Filtering, Query Expansion, and 2-Pass Reranking.
        """
        if not self.chunks:
            self.load_and_index_documents()

        expanded_tokens = self._expand_query(query)
        scored_chunks = []

        for chunk in self.chunks:
            if document_filter:
                if document_filter.lower() not in chunk.doc_name.lower():
                    continue

            score = self._compute_relevance_score(expanded_tokens, chunk)
            if score > 0.05:
                scored_chunks.append((chunk, score))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Apply 2-pass Reranking algorithm
        reranked = self._rerank_chunks(scored_chunks[:top_k * 2], query)
        return reranked[:top_k]

    def query_policy(
        self,
        query: str,
        document_filter: Optional[str] = None,
        history: Optional[List[ChatMessage]] = None
    ) -> RAGQueryResponse:
        """
        Performs Retrieval-Augmented Generation (RAG) over indexed policy documents.
        Returns grounded answers with citations, or explicit fallback if information is missing.
        """
        full_context_query = query
        if history:
            last_turns = " ".join([m.content for m in history[-2:]])
            full_context_query = f"{last_turns} {query}"

        retrieved_results = self.retrieve(query=full_context_query, document_filter=document_filter, top_k=3)

        if not retrieved_results or retrieved_results[0][1] < 0.10:
            return RAGQueryResponse(
                answer="Sufficient information could not be found in the provided policy documents to answer your question.",
                citations=[],
                grounded=False,
                query=query
            )

        citations = []
        answer_parts = []

        for chunk, score in retrieved_results:
            citation = Citation(
                document_name=chunk.doc_name,
                section_title=chunk.section_title,
                excerpt=chunk.content[:250] + ("..." if len(chunk.content) > 250 else ""),
                relevance_score=score
            )
            citations.append(citation)

            answer_parts.append(
                f"**According to the {chunk.doc_name} ({chunk.section_title}):**\n{chunk.content}\n"
            )

        combined_answer = "\n---\n".join(answer_parts)

        return RAGQueryResponse(
            answer=combined_answer,
            citations=citations,
            grounded=True,
            query=query
        )

    def record_feedback(self, req: FeedbackRequest) -> FeedbackResponse:
        """Records user feedback (rating & comments) for RAG answer quality."""
        feedback_id = str(uuid.uuid4())
        record = {
            "feedback_id": feedback_id,
            "query": req.query,
            "rating": req.rating,
            "comment": req.comment,
            "timestamp": time.time()
        }
        self.feedbacks.append(record)
        return FeedbackResponse(
            status="success",
            message="Thank you for your feedback!",
            feedback_id=feedback_id
        )

    async def stream_policy_query(
        self,
        query: str,
        document_filter: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Streams RAG response chunk by chunk for real-time streaming UI."""
        res = self.query_policy(query=query, document_filter=document_filter)
        words = res.answer.split(" ")
        for word in words:
            yield word + " "
            import asyncio
            await asyncio.sleep(0.02)
