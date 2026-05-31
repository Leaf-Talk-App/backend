"""
Script de diagnóstico — rode antes do deploy ou para debug.
Uso: python check_env.py
"""
import os
import sys

REQUIRED = ["MONGO_URL", "JWT_SECRET"]
OPTIONAL = [
    "DATABASE_NAME", "GEMINI_API_KEY",
    "EMAIL_USERNAME", "EMAIL_PASSWORD", "EMAIL_FROM",
    "FRONTEND_URL", "CORS_ORIGINS",
    "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
]

print("=== Leaf Talk — Environment Check ===\n")
ok = True

for key in REQUIRED:
    val = os.environ.get(key)
    if not val:
        print(f"[FAIL] {key} — AUSENTE (obrigatório)")
        ok = False
    else:
        preview = val[:12] + "..." if len(val) > 12 else val
        print(f"[ OK ] {key} = {preview}")

print()
for key in OPTIONAL:
    val = os.environ.get(key, "")
    status = "SET " if val else "---"
    print(f"[{status}] {key}")

print()
if ok:
    print("✅  Variáveis obrigatórias OK")
else:
    print("❌  Faltam variáveis obrigatórias — o backend não iniciará corretamente")
    sys.exit(1)

# Testa conexão MongoDB
try:
    from pymongo import MongoClient
    client = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    print("✅  MongoDB Atlas: conexão OK")
except Exception as e:
    print(f"❌  MongoDB Atlas: {e}")
