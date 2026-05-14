def verification_email_template(name: str, code: str):
    return f"""
    <div style="font-family: Arial; padding: 20px;">
        <h1>Leaf Talk</h1>
        <p>Olá, {name}!</p>
        <p>Use o código abaixo para verificar sua conta:</p>
        <div style="font-size: 28px; font-weight: 700; letter-spacing: 6px; color: #2d4a2b;">
            {code}
        </div>
        <p>Se você não criou essa conta, ignore este email.</p>
    </div>
    """


def reset_password_email_template(name: str, reset_link: str):
    return f"""
    <div style="font-family: Arial; padding: 20px;">
        <h1>Leaf Talk</h1>
        <p>Olá, {name}!</p>
        <p>Recebemos uma solicitação para redefinir sua senha.</p>
        <a
            href="{reset_link}"
            style="display:inline-block;padding:12px 20px;background:#16a34a;color:white;text-decoration:none;border-radius:8px;"
        >
            Redefinir senha
        </a>
        <p>Este link expira em 30 minutos.</p>
    </div>
    """
