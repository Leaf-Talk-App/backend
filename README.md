<div align="center">

# 🌿 Leaf Talk — Backend (API)

### FastAPI + MongoDB + WebSockets + IA (Claude)

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](#)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](#)
[![MongoDB](https://img.shields.io/badge/MongoDB-Motor%20(async)-47A248?logo=mongodb&logoColor=white)](#)
[![Anthropic](https://img.shields.io/badge/IA-Claude%20Haiku-D97757?logo=anthropic&logoColor=white)](#)
[![Render](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render&logoColor=white)](#)

API do **Leaf Talk**: autenticação, conversas em tempo real, grupos, uploads, o assistente **Humberto** (IA) e o **Leaf Quiz**.

</div>

---

## 🧱 Stack

- **FastAPI** + **Uvicorn**
- **MongoDB** via **Motor** (async)
- **JWT** (python-jose) · senhas com **bcrypt** (passlib)
- **WebSockets** (tempo real) · **APScheduler** (entrega de mensagens agendadas)
- **Anthropic SDK** — Humberto roda no **Claude Haiku**
- **Cloudinary** (mídia) · **slowapi** (rate limiting)

---

## ⚙️ Rodando localmente

> Requer **Python 3.12+** e um MongoDB acessível.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # preencha as variáveis
uvicorn app.main:app --reload                        # http://localhost:8000
```

Docs interativas: **`/docs`** (Swagger) · health check: **`/health`**.

### Variáveis de ambiente
| Variável | Descrição |
|----------|-----------|
| `MONGO_URL` | String de conexão do MongoDB |
| `JWT_SECRET` | Segredo do JWT (**obrigatório**, sem default) |
| `JWT_EXPIRE_MINUTES` | Validade do token (padrão: 7 dias) |
| `ANTHROPIC_API_KEY` | Chave do Claude (Humberto) — **só no backend** |
| `CORS_ORIGINS` | Origens extras permitidas (separadas por vírgula) |
| `CLOUDINARY_URL` *(ou KEY/SECRET/NAME)* | Storage de mídia (opcional; sem ela, salva em disco) |
| `BREVO_API_KEY` / `EMAIL_*` | Envio de e-mail (verificação/recuperação) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Login com Google (opcional) |
| `QUIZ_ADMIN_KEY` | Chave para zerar o ranking do quiz (`POST /quiz/reset`) |
| `LOG_LEVEL` | Nível de log (ex.: `WARNING` em produção) |

> 🔐 Nunca comite segredos. Tudo vem do ambiente.

---

## 🔌 Principais rotas

| Grupo | Rotas |
|-------|-------|
| **Auth** | `POST /auth/register` · `/auth/login` · `/auth/logout` · `/auth/verify-email` · `/auth/forgot-password` · `/auth/reset-password` · `/auth/google/*` |
| **Usuários** | `GET /users/me` · `PATCH /users/profile` · `GET /users/search` · `POST /users/block` · `GET /users/{id}` |
| **Conversas** | `POST /chats/create` · `GET /chats/my` · `GET /chats/{id}` · pin/mute/archive |
| **Mensagens** | `POST /messages/send` · `GET /messages/{chat_id}` · editar/apagar/favoritar |
| **Grupos** | `POST /groups/create` · membros/admins · `POST /groups/update` (nome, foto, regras) · `/groups/{id}/messages` |
| **Humberto (IA)** | `POST /ai/chat` · `GET /ai/history` · `POST /ai/confirm/{task}` · `GET /ai/pending` |
| **Upload** | `POST /upload/image` · `/upload/audio` · `/upload/file` · `GET /upload/download` |
| **WebSocket** | `WS /ws/{user_id}?token=…` (autenticado) |
| **Quiz** | `GET /quiz/questions` · `POST /quiz/submit` · `GET /quiz/ranking` · `GET /quiz/stats` · `POST /quiz/reset?key=…` |

---

## 🗂️ Estrutura

```
app/
├── main.py            # app, CORS, headers de segurança, rate limit, routers
├── dependencies.py    # get_current_user (JWT + token_version)
├── core/              # config, database, security, websocket, ratelimit, logger, cloudinary, email
└── modules/
    ├── auth/          # cadastro, login, logout, verificação, Google
    ├── users/         # perfil, busca, bloqueio, presença
    ├── chats/         # conversas 1:1
    ├── messages/      # mensagens (envio, histórico, edição)
    ├── groups/        # grupos + administração
    ├── ai/            # Humberto: chat, RAG, ações (enviar/agendar)
    ├── scheduler/     # entrega das mensagens agendadas (APScheduler)
    ├── upload/        # uploads + proxy de download
    ├── websocket/     # canal de tempo real
    └── quiz/          # Leaf Quiz (banco de perguntas, ranking)
```

---

## 🧠 Humberto (IA)

Roda no **Claude Haiku** (Anthropic). Conversa sobre qualquer assunto, analisa imagem/PDF e entende **comandos de ação**: ao pedir para *enviar* ou *agendar* uma mensagem, ele monta um **card de confirmação** — só executa quando o usuário confirma. Mensagens agendadas são entregues pelo **APScheduler** no horário certo.

---

## 🛡️ Segurança

- **Autenticação** JWT; **logout invalida o token** no servidor (via `token_version`).
- Senhas com **bcrypt** (custo 12); pbkdf2 antigo ainda valida.
- **Autorização por recurso**: só participante lê/escreve em uma conversa; grupos checam membership; WebSocket exige token válido.
- **Rate limiting** (login, registro, recuperação, envio) e **headers** de segurança.
- **Uploads** com whitelist de tipo, limite de tamanho e nomes em **UUID** (sem path traversal).
- **CORS** restrito às origens do frontend. **Logs** de eventos críticos sem dados sensíveis.

---

## 🎯 Leaf Quiz

Endpoints públicos para a experiência ao vivo. As perguntas são sorteadas e a **correção acontece no servidor** (o gabarito nunca vai para o cliente). Ranking ordenado por **acertos → tempo → quem terminou antes**. Zere o ranking entre turmas com `POST /quiz/reset?key=$QUIZ_ADMIN_KEY`.

---

<div align="center">

Feito com 🌿 pela equipe **Leaf**.

</div>
