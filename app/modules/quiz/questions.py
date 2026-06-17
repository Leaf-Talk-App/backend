"""Perguntas do Leaf Quiz (apresentação). A resposta correta (índice em `opcoes`)
fica SÓ no backend — o frontend recebe as perguntas sem o gabarito e a correção
é feita no servidor (impede cola pelo DevTools)."""

QUESTIONS = [
    {
        "pergunta": "Qual tecnologia permite que um sistema aprenda padrões a partir de dados sem ser explicitamente programado para cada situação?",
        "opcoes": ["API REST", "Machine Learning", "Blockchain", "Criptografia"],
        "answer": 1,
    },
    {
        "pergunta": "Qual é o principal benefício da criptografia ponta a ponta?",
        "opcoes": [
            "Backup automático",
            "Somente remetente e destinatário podem ler",
            "Maior velocidade",
            "Menor consumo",
        ],
        "answer": 1,
    },
    {
        "pergunta": "O que é NLP?",
        "opcoes": [
            "Banco de Dados",
            "Processamento de Linguagem Natural",
            "Rede Neural Convolucional",
            "API",
        ],
        "answer": 1,
    },
    {
        "pergunta": "Qual tecnologia normalmente mantém chats em tempo real?",
        "opcoes": ["FTP", "WebSocket", "SMTP", "Bluetooth"],
        "answer": 1,
    },
    {
        "pergunta": "O que caracteriza IA Generativa?",
        "opcoes": ["Armazenar dados", "Criar conteúdo novo", "Comprimir arquivos", "Monitorar rede"],
        "answer": 1,
    },
    {
        "pergunta": "Qual arquitetura é usada por modelos como ChatGPT?",
        "opcoes": ["CNN", "RNN", "Transformer", "Perceptron"],
        "answer": 2,
    },
    {
        "pergunta": "Qual banco é mais usado para alta escalabilidade de mensagens?",
        "opcoes": ["Excel", "TXT", "NoSQL", "PDF"],
        "answer": 2,
    },
    {
        "pergunta": "O que são notificações push?",
        "opcoes": ["Atualizações em tempo real", "Backup", "Compressão", "Firewall"],
        "answer": 0,
    },
    {
        "pergunta": "Qual recurso pode usar IA em aplicativos de conversa?",
        "opcoes": ["Resposta inteligente", "Volume", "Brilho", "Instalação"],
        "answer": 0,
    },
    {
        "pergunta": "Qual método é amplamente usado para autenticação moderna?",
        "opcoes": ["Token", "DNS", "HTML", "Cache"],
        "answer": 0,
    },
]


def public_questions():
    """Perguntas SEM o gabarito (o que vai pro frontend)."""
    return [
        {"id": i, "pergunta": q["pergunta"], "opcoes": q["opcoes"]}
        for i, q in enumerate(QUESTIONS)
    ]
