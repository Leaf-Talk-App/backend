from pydantic import BaseModel, Field


class QuizSubmitSchema(BaseModel):
    # nome curto (anti-spam/visual): 1..40 chars
    name: str = Field(min_length=1, max_length=40)
    # uma resposta (índice da opção) por pergunta; -1 = não respondida
    answers: list[int] = Field(default_factory=list)
    # tempo total medido no cliente (ms) — só p/ desempate no ranking
    duration_ms: int = Field(default=0, ge=0)
