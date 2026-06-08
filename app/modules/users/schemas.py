from pydantic import BaseModel
from typing import Optional

class UpdateUserSchema(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None
    # Telefone apenas armazenado/exibido — SEM verificação por SMS.
    # Se um dia quiser verificar por SMS (gratuito p/ começar):
    #   - Twilio Verify: trial grátis (crédito inicial) + número de teste.
    #   - Firebase Phone Auth: free tier (cota mensal de verificações).
    # Implicaria um endpoint extra (enviar código / confirmar) — não feito aqui.
    phone: Optional[str] = None
    searchable: Optional[bool] = None
    
class BlockUserSchema(BaseModel):
    user_id: str