import logging
import os

# Nível por ambiente: LOG_LEVEL=WARNING em produção (Render), DEBUG/INFO em dev.
_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
_level = getattr(logging, _level_name, logging.INFO)

logging.basicConfig(
    level=_level,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

logger = logging.getLogger("leaf-talk")

# Logger dedicado a eventos de segurança (login, token, 403, upload). NUNCA
# registra senha, token ou conteúdo de mensagem — só metadados (id, ip, tipo).
security_logger = logging.getLogger("leaf-talk.security")
