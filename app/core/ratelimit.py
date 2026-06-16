"""Rate limiting (slowapi) — protege endpoints sensíveis de brute-force/abuso.

O limiter é por IP (get_remote_address). Em produção atrás do Render, o IP real
vem em X-Forwarded-For; slowapi usa o remote address — suficiente p/ travar
brute-force simples de login/registro. Limites aplicados via @limiter.limit nas
rotas (login, registro, recuperação de senha, envio de mensagem).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
