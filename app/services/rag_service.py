import os
import re
import math
from typing import List, Dict, Any, Tuple, Optional, AsyncGenerator
from app.schemas.rag import Citation, RAGQueryResponse, ChatMessage

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
    def __init__(self, doc_name: str, section_title: str, content: str):
        self.doc_name = doc_name
        self.section_title = section_title
        self.content = content
        self.tokens = self._tokenize(content)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        words = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
        return [w for w in words if w not in STOP_WORDS]


class RAGService:
    _instance = None

    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.load_and_index_documents()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = RAGService()
        return cls._instance

    def load_and_index_documents(self):
        """Indexes markdown policy documents from the policies directory."""
        self.chunks = []
        if not os.path.exists(POLICIES_DIR):
            return

        for filename in os.listdir(POLICIES_DIR):
            if filename.endswith(".md"):
                file_path = os.path.join(POLICIES_DIR, filename)
                doc_title = filename.replace(".md", "").replace("_", " ").title()
                
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()

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
                            content=body
                        ))

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
        """
        Hybrid similarity scoring combining query token overlap & title matching.
        """
        if not query_tokens or not chunk.tokens:
            return 0.0

        # Term frequency matching in chunk content
        content_matches = sum(1 for token in query_tokens if token in chunk.tokens)
        if content_matches == 0:
            return 0.0

        content_score = content_matches / (len(set(query_tokens)) + 1e-5)

        # Title bonus matching
        title_tokens = set(re.findall(r'\b[a-zA-Z0-9]+\b', chunk.section_title.lower() + " " + chunk.doc_name.lower()))
        title_matches = sum(1 for token in query_tokens if token in title_tokens)
        title_score = title_matches * 0.5

        total_score = content_score + title_score
        return round(total_score, 3)

    def retrieve(
        self,
        query: str,
        document_filter: Optional[str] = None,
        top_k: int = 3
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Retrieves top-K most relevant policy chunks matching the query.
        Supports metadata filtering.
        """
        if not self.chunks:
            self.load_and_index_documents()

        expanded_tokens = self._expand_query(query)
        scored_chunks = []

        for chunk in self.chunks:
            # Metadata filter check
            if document_filter:
                if document_filter.lower() not in chunk.doc_name.lower():
                    continue

            score = self._compute_relevance_score(expanded_tokens, chunk)
            if score > 0.05:
                scored_chunks.append((chunk, score))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]

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
        # Consider follow-up query context from conversation history
        full_context_query = query
        if history:
            last_turns = " ".join([m.content for m in history[-2:]])
            full_context_query = f"{last_turns} {query}"

        retrieved_results = self.retrieve(query=full_context_query, document_filter=document_filter, top_k=3)

        # Check threshold for missing information fallback
        if not retrieved_results or retrieved_results[0][1] < 0.12:
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

            # Grounded answer synthesis per matching section
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
