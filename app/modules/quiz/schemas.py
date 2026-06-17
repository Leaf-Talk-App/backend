from pydantic import BaseModel, Field


class QuizResponse(BaseModel):
    id: int  # id da pergunta (no banco de 50)
    answer: int = -1  # índice da opção escolhida; -1 = não respondida


class QuizSubmitSchema(BaseModel):
    # nome curto (anti-spam/visual): 1..40 chars
    name: str = Field(min_length=1, max_length=40)
    # respostas por pergunta (id + opção escolhida) — cada device recebeu um
    # sorteio diferente, então a correção é por id, não por posição
    responses: list[QuizResponse] = Field(default_factory=list)
    # tempo total medido no cliente (ms) — só p/ desempate no ranking
    duration_ms: int = Field(default=0, ge=0)
