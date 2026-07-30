import os
import re
import math
import uuid
import time
import httpx
from typing import List, Dict, Any, Tuple, Optional, AsyncGenerator
from app.core.config import settings
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
        Supports Incremental Indexing (only re-indexes modified/new files) and PDF/Markdown/TXT/CSV parsing.
        """
        if not os.path.exists(POLICIES_DIR):
            return

        if force_reindex:
            self.chunks = []
            self.indexed_files_mtime = {}

        current_files = os.listdir(POLICIES_DIR)

        for filename in current_files:
            file_path = os.path.join(POLICIES_DIR, filename)
            mtime = os.path.getmtime(file_path)

            if not force_reindex and file_path in self.indexed_files_mtime:
                if self.indexed_files_mtime[file_path] >= mtime:
                    continue

            text = ""
            doc_title = os.path.splitext(filename)[0].replace("_", " ").title()

            if filename.endswith(".md") or filename.endswith(".txt") or filename.endswith(".csv"):

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                except Exception:
                    continue
            elif filename.endswith(".pdf"):
                text = self._extract_text_from_pdf(file_path)
            else:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    continue

            self.chunks = [c for c in self.chunks if c.file_path != file_path]
            self.indexed_files_mtime[file_path] = mtime

            if "## " in text:
                raw_sections = re.split(r'\n(?=##\s+)', text)
            else:
                paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
                raw_sections = []
                current_block = []
                current_len = 0
                for p in paragraphs:
                    current_block.append(p)
                    current_len += len(p)
                    if current_len >= 400:
                        raw_sections.append("\n\n".join(current_block))
                        current_block = []
                        current_len = 0
                if current_block:
                    raw_sections.append("\n\n".join(current_block))

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
                    # Extract header candidate from first non-empty line
                    section_title = lines[0][:50].strip(" -#*:") if len(lines[0]) < 60 else "Policy Detail"
                    body = "\n".join(lines).strip()

                if body:
                    self.chunks.append(DocumentChunk(
                        doc_name=doc_title,
                        section_title=section_title,
                        content=body,
                        file_path=file_path
                    ))

    def delete_document(self, filename: str) -> bool:
        """Deletes a document from knowledge base policies directory."""
        file_path = os.path.join(POLICIES_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            self.chunks = [c for c in self.chunks if c.file_path != file_path]
            if file_path in self.indexed_files_mtime:
                del self.indexed_files_mtime[file_path]
            return True
        return False

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extracts text from PDF documents with fallback handling."""
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
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(file_path)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            except Exception:
                pass

        if not text.strip():
            try:
                with open(file_path, "rb") as f:
                    content = f.read().decode("utf-8", errors="ignore")
                    text = re.sub(r'[^\x20-\x7E\n\r\t]', ' ', content)
            except Exception:
                pass

        if not text.strip():
            text = f"## Policy Document Content\nExtracted content from file {os.path.basename(file_path)}."
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
            # Check raw string overlap for single word queries like 'bonus'
            chunk_lower = chunk.content.lower()
            if any(q in chunk_lower for q in query_tokens):
                content_matches = 1

        if content_matches == 0:
            return 0.0

        content_score = content_matches / (len(set(query_tokens)) + 1e-5)

        title_tokens = set(re.findall(r'\b[a-zA-Z0-9]+\b', chunk.section_title.lower() + " " + chunk.doc_name.lower()))
        title_matches = sum(1 for token in query_tokens if token in title_tokens)
        title_score = title_matches * 0.5

        return round(content_score + title_score, 3)

    def _rerank_chunks(self, scored_chunks: List[Tuple[DocumentChunk, float]], query: str) -> List[Tuple[DocumentChunk, float]]:
        """Reranking stage using Reciprocal Rank Fusion (RRF) and exact term matching."""
        if not scored_chunks:
            return []

        query_lower = query.lower()
        reranked = []
        for rank, (chunk, base_score) in enumerate(scored_chunks):
            rrf_score = 1.0 / (60 + rank + 1)
            exact_bonus = 0.3 if query_lower in chunk.content.lower() else 0.0
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
        """Retrieves top-K most relevant policy chunks matching the query."""
        if not self.chunks:
            self.load_and_index_documents()

        expanded_tokens = self._expand_query(query)
        scored_chunks = []

        for chunk in self.chunks:
            if document_filter:
                if document_filter.lower() not in chunk.doc_name.lower():
                    continue

            score = self._compute_relevance_score(expanded_tokens, chunk)
            if score > 0.001:
                scored_chunks.append((chunk, score))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        reranked = self._rerank_chunks(scored_chunks[:top_k * 2], query)
        return reranked[:top_k]

    def _generate_with_groq(self, query: str, context: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Calls Groq API (llama-3.3-70b-versatile) with strict system instructions:
        Answer strictly using ONLY the provided document context.
        Returns tuple of (answer_text, error_message).
        """
        api_key = getattr(settings, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
        if not api_key:
            return None, "No GROQ_API_KEY configured"

        prompt = f"""You are a strict, precise document Q&A assistant. Your task is to answer the user's question using ONLY the provided context extracted from the uploaded document(s).

STRICT COMPLIANCE RULES:
1. You MUST answer the question using ONLY information directly stated in the CONTEXT below.
2. If the user's question CANNOT be answered completely and strictly using the CONTEXT below, respond with EXACTLY this phrase and nothing else:
"Sufficient information could not be found in the provided policy documents to answer your question."
3. Do NOT use any external knowledge, background information, or make up any details beyond the provided context.
4. Keep the answer concise, accurate, and directly grounded in the text.

CONTEXT FROM UPLOADED DOCUMENTS:
{context}

USER QUESTION:
{query}
"""

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are a precise, document-grounded assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "").strip()
                        return content, None
                else:
                    return None, f"Groq API Error {response.status_code}: {response.text[:150]}"
        except Exception as e:
            return None, str(e)
        return None, "No response choices returned from Groq API"

    def _generate_with_gemini(self, query: str, context: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Calls Gemini 2.0 Flash API with strict system instructions.
        Returns tuple of (answer_text, error_message).
        """
        api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return None, "No GEMINI_API_KEY configured"

        prompt = f"""You are a strict, precise document Q&A assistant. Your task is to answer the user's question using ONLY the provided context extracted from the uploaded document(s).

STRICT COMPLIANCE RULES:
1. You MUST answer the question using ONLY information directly stated in the CONTEXT below.
2. If the user's question CANNOT be answered completely and strictly using the CONTEXT below, respond with EXACTLY this phrase and nothing else:
"Sufficient information could not be found in the provided policy documents to answer your question."
3. Do NOT use any external knowledge, background information, or make up any details beyond the provided context.
4. Keep the answer concise, accurate, and directly grounded in the text.

CONTEXT FROM UPLOADED DOCUMENTS:
{context}

USER QUESTION:
{query}
"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        try:
            with httpx.Client(timeout=12.0) as client:
                response = client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip(), None
                elif response.status_code == 429:
                    return None, "Gemini API Quota Exceeded (429 Rate Limit)."
                else:
                    return None, f"Gemini API Error {response.status_code}: {response.text[:150]}"
        except Exception as e:
            return None, str(e)
        return None, "No candidates returned from Gemini API"

    def query_policy(
        self,
        query: str,
        document_filter: Optional[str] = None,
        history: Optional[List[ChatMessage]] = None
    ) -> RAGQueryResponse:
        """
        Performs Retrieval-Augmented Generation (RAG) using Groq API (Llama 3.3 70B) over uploaded documents.
        Answers strictly using ONLY the provided document context.
        """
        full_context_query = query
        if history:
            last_turns = " ".join([m.content for m in history[-2:]])
            full_context_query = f"{last_turns} {query}"

        # Friendly greeting handler for general conversational greetings
        clean_query = query.strip().lower()
        if clean_query in ["hi", "hii", "hello", "hey", "help", "greetings"]:
            return RAGQueryResponse(
                answer="Hello! 👋 Ask me any question about your uploaded policy documents (e.g. meal limits, flight booking rules, lodging caps, or bonus requirements).",
                citations=[],
                grounded=True,
                query=query
            )

        retrieved_results = self.retrieve(query=full_context_query, document_filter=document_filter, top_k=3)

        fallback_msg = "Sufficient information could not be found in the provided policy documents to answer your question."

        if not retrieved_results or retrieved_results[0][1] < 0.001:
            return RAGQueryResponse(
                answer=fallback_msg,
                citations=[],
                grounded=False,
                query=query
            )

        citations = []
        context_blocks = []

        for chunk, score in retrieved_results:
            citations.append(Citation(
                document_name=chunk.doc_name,
                section_title=chunk.section_title,
                excerpt=chunk.content[:250] + ("..." if len(chunk.content) > 250 else ""),
                relevance_score=score
            ))
            context_blocks.append(f"[{chunk.doc_name} - {chunk.section_title}]\n{chunk.content}")

        combined_context = "\n\n---\n\n".join(context_blocks)

        # 1. Try Groq API first (Llama-3.3-70b-versatile)
        groq_answer, error_msg = self._generate_with_groq(query=query, context=combined_context)

        if groq_answer:
            final_answer = groq_answer
            is_grounded = fallback_msg.lower() not in groq_answer.lower()
        else:
            # 2. Fallback to Gemini 2.0 Flash API if configured
            gemini_answer, gem_err = self._generate_with_gemini(query=query, context=combined_context)
            if gemini_answer:
                final_answer = gemini_answer
                is_grounded = fallback_msg.lower() not in gemini_answer.lower()
            else:
                # 3. Local grounded synthesis fallback
                final_answer = "\n---\n".join([
                    f"**According to {chunk.doc_name} ({chunk.section_title}):**\n{chunk.content}"
                    for chunk, _ in retrieved_results
                ])
                is_grounded = True

        return RAGQueryResponse(
            answer=final_answer,
            citations=citations if is_grounded else [],
            grounded=is_grounded,
            query=query
        )


    def record_feedback(self, req: FeedbackRequest) -> FeedbackResponse:
        """Records user feedback for RAG quality."""
        feedback_id = str(uuid.uuid4())
        self.feedbacks.append({
            "feedback_id": feedback_id,
            "query": req.query,
            "rating": req.rating,
            "comment": req.comment,
            "timestamp": time.time()
        })
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
        """Streams RAG response token by token."""
        res = self.query_policy(query=query, document_filter=document_filter)
        words = res.answer.split(" ")
        for word in words:
            yield word + " "
            import asyncio
            await asyncio.sleep(0.02)
