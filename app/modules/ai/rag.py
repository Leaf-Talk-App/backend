"""RAG simples do Humberto: recupera perguntas/respostas relevantes do dataset
do Leaf Talk e injeta como contexto no prompt. Sem dependências externas — usa
sobreposição de termos + similaridade de strings (difflib). O objetivo é ENSINAR
o Humberto (identidade, fundadores, recursos), não limitar suas funções.
"""
import json
import os
import re
import difflib

_DATA: list[tuple[str, str]] | None = None

_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "knowledge", "leaf_talk_rag_dataset.json"
)

# termos muito comuns que não ajudam a discriminar
_STOP = {
    "o", "a", "os", "as", "de", "do", "da", "dos", "das", "e", "que", "como",
    "para", "por", "com", "um", "uma", "no", "na", "em", "meu", "minha", "eu",
    "posso", "qual", "quais", "quem", "é", "ser", "the", "of",
}


def _norm(s: str) -> str:
    return re.sub(r"[^0-9a-zà-ú ]", " ", (s or "").lower())


def _tokens(s: str) -> set[str]:
    return {t for t in _norm(s).split() if t and t not in _STOP and len(t) > 2}


def _load() -> list[tuple[str, str]]:
    global _DATA
    if _DATA is None:
        try:
            with open(_DATASET_PATH, encoding="utf-8") as f:
                raw = json.load(f)
            seen, items = set(), []
            for it in raw:
                q = (it.get("question") or "").strip()
                a = (it.get("answer") or "").strip()
                if not q or not a:
                    continue
                key = q.lower()
                if key in seen:
                    continue
                seen.add(key)
                items.append((q, a))
            _DATA = items
        except Exception:
            _DATA = []
    return _DATA


def retrieve(query: str, k: int = 4, threshold: float = 0.18):
    """Top-k pares (pergunta, resposta) mais relevantes para a query."""
    data = _load()
    if not data or not (query or "").strip():
        return []

    q_tokens = _tokens(query)
    q_norm = _norm(query)
    scored = []
    for question, answer in data:
        d_tokens = _tokens(question)
        overlap = (len(q_tokens & d_tokens) / len(q_tokens)) if q_tokens else 0.0
        ratio = difflib.SequenceMatcher(None, q_norm, _norm(question)).ratio()
        score = 0.7 * overlap + 0.3 * ratio
        scored.append((score, question, answer))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [(q, a) for s, q, a in scored if s >= threshold][:k]


def context_block(query: str) -> str:
    """Bloco de contexto p/ anexar ao system prompt (vazio se nada relevante)."""
    top = retrieve(query)
    if not top:
        return ""
    lines = [
        "\n\nBASE DE CONHECIMENTO DO LEAF TALK (use quando for relevante para "
        "responder com precisão sobre o Leaf Talk, o Humberto, os fundadores e os "
        "recursos; não invente fatos além destes):",
    ]
    for q, a in top:
        lines.append(f"- P: {q}\n  R: {a}")
    return "\n".join(lines)
