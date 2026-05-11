def verification_email_template(
    name: str,
    verification_link: str
):
    return f"""
    <div style="font-family: Arial; padding: 20px;">
        <h1>Leaf Talk</h1>

        <p>Olá, {name}!</p>

        <p>
            Clique no botão abaixo para verificar sua conta:
        </p>

        <a
            href="{verification_link}"
            style="
                display:inline-block;
                padding:12px 20px;
                background:#16a34a;
                color:white;
                text-decoration:none;
                border-radius:8px;
            "
        >
            Verificar Conta
        </a>

        <p>
            Se você não criou essa conta, ignore este email.
        </p>
    </div>
    """