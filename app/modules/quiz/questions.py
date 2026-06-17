"""Banco de perguntas do Leaf Quiz (apresentação).

A cada acesso, o servidor sorteia QUIZ_SIZE perguntas em ordem aleatória (cada
dispositivo recebe um conjunto/ordem diferente). A resposta correta (índice em
`opcoes`) fica SÓ no backend — o frontend nunca recebe o gabarito; a correção é
feita no servidor pelo `id` da pergunta.
"""
import random

QUIZ_SIZE = 10  # quantas perguntas cada pessoa responde por sessão

QUESTIONS = [
    {
        "pergunta": "Quais são os únicos dados que você precisa passar para conseguir criar uma conta no Leaf?",
        "opcoes": [
            "Nome, E-mail e Senha",
            "Nome, Telefone, E-mail e senha",
            "Nome, Telefone e CPF",
            "Apenas o nome é o necessário",
        ],
        "answer": 0,
    },
    {
        "pergunta": "Selecione a alternativa que diz TUDO o que o Leaf oferece:",
        "opcoes": [
            "Envio de mensagens, arquivos e IA integrada",
            "ChatBot e envio de mensagens",
            "Agendamento de mensagens e ChatBot",
            "Criptografia, IA integrada, envio de mensagens e arquivos",
        ],
        "answer": 3,
    },
    {
        "pergunta": "O que o assistente Humberto do Leaf faz?",
        "opcoes": [
            "Recebe dados e guarda no banco de dados",
            "Apenas cria agendamentos de mensagens",
            "Entende perguntas, responde e executa tarefas agendadas",
            "Faz o trabalho de um Chatbot convencional",
        ],
        "answer": 2,
    },
    {
        "pergunta": "O suporte do Leaf é bom?",
        "opcoes": [
            "Péssimo (não quero chaveiro)",
            "Sim, possui o número do Alan na aplicação para quaisquer dúvidas sobre o app",
            "Não, muito ruim",
            "Não sei",
        ],
        "answer": 1,
    },
    {
        "pergunta": "Como encontrar um amigo no Leaf?",
        "opcoes": [
            "Escaneando seu código QR",
            "Estando na mesma rede local que o seu amigo",
            "Consigo mandar mensagens para qualquer pessoa disponível",
            "Conectar por Bluetooth",
        ],
        "answer": 2,
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
        "pergunta": "Qual tecnologia normalmente mantém chats em tempo real?",
        "opcoes": ["FTP", "WebSocket", "SMTP", "Bluetooth"],
        "answer": 1,
    },
    {
        "pergunta": "O que caracteriza o conceito de Inteligência Artificial Generativa?",
        "opcoes": [
            "A capacidade de apenas armazenar e indexar dados estruturados",
            "A habilidade de processar dados existentes para criar um conteúdo totalmente novo",
            "Algoritmos focados estritamente em compactar e extrair arquivos",
            "Ferramentas exclusivas para monitorar o tráfego de uma rede",
        ],
        "answer": 1,
    },
    {
        "pergunta": "Qual banco é mais usado para alta escalabilidade de mensagens?",
        "opcoes": ["SQL", "TXT", "NoSQL", "PDF"],
        "answer": 2,
    },
    {
        "pergunta": "No contexto de automações de chat, o que significa a sigla NLP?",
        "opcoes": [
            "Novo Protocolo de Transmissão Local (Network Local Protocol)",
            "Processamento de Linguagem Natural (Natural Language Processing)",
            "Rede Neural Convolucional Aplicada (Network Neural Processing)",
            "Interface de Programação de Aplicações Avançada (Advanced API)",
        ],
        "answer": 1,
    },
    {
        "pergunta": "Se você agendar uma mensagem para um amigo e se arrepender antes do horário de envio, o que o Leaf permite fazer?",
        "opcoes": [
            "Cancelar ou editar o agendamento antes do disparo",
            "Nada, o envio é obrigatório após programado",
            "Apagar a conta para cancelar o envio",
            "A mensagem é enviada e apagada depois",
        ],
        "answer": 0,
    },
    {
        "pergunta": "Qual é a principal função das rotas REST (HTTP) no ecossistema do Leaf Talk?",
        "opcoes": [
            "Manter a conexão do chat aberta continuamente em tempo real",
            "Gerenciar ações estruturadas como cadastro, login e salvamento de dados",
            "Enviar notificações por Bluetooth",
            "Substituir o uso de internet na aplicação",
        ],
        "answer": 1,
    },
    {
        "pergunta": "Além do aplicativo web para computadores, em qual outro tipo de ambiente o Leaf Talk foi projetado para rodar?",
        "opcoes": [
            "Apenas em smart TVs",
            "Em dispositivos móveis (aplicativo mobile)",
            "Exclusivamente em smartwatches",
            "Linhas de comando de servidores antigos",
        ],
        "answer": 1,
    },
    {
        "pergunta": "O que é um Token JWT, utilizado na segurança do Leaf Talk?",
        "opcoes": [
            "Um tipo de banco de dados criptografado",
            "Um protocolo de transferência de arquivos pesados",
            "Uma credencial de segurança temporária que valida a identidade do usuário logado",
            "O nome do assistente virtual do sistema",
        ],
        "answer": 2,
    },
    {
        "pergunta": 'Para que serve a funcionalidade de "Configuração de Privacidade" no Leaf Talk?',
        "opcoes": [
            "Para mudar a cor do tema do aplicativo",
            "Para definir quem pode encontrar seu perfil ou ver suas informações públicas",
            "Para bloquear o uso de Wi-Fi no aplicativo",
            "Para excluir o histórico de mensagens automaticamente",
        ],
        "answer": 1,
    },
    {
        "pergunta": "O que acontece tecnicamente quando uma conexão WebSocket é estabelecida no Leaf?",
        "opcoes": [
            "O servidor encerra a sessão para economizar recursos",
            "Um canal bidirecional permanente é aberto entre o cliente e o servidor para troca instantânea de dados",
            "O banco de dados é inteiramente baixado no dispositivo do usuário",
            "As mensagens passam a ser enviadas por SMS padrão",
        ],
        "answer": 1,
    },
    {
        "pergunta": "Como o assistente de automação do Leaf Talk sabe que deve realizar uma ação de agendamento?",
        "opcoes": [
            "Ele tenta adivinhar o comportamento do usuário por inteligência preditiva passiva",
            "Através de uma solicitação ou comando de texto explícito enviado pelo usuário no chat",
            "Ele executa ações aleatórias ao longo do dia",
            "Monitorando as redes sociais externas do usuário",
        ],
        "answer": 1,
    },
    {
        "pergunta": 'O que significa o conceito de "Escalabilidade" em um sistema de chat como o Leaf Talk?',
        "opcoes": [
            "A habilidade do sistema de funcionar sem nenhuma conexão com a internet",
            "O tamanho físico que os servidores ocupam na empresa",
            "A capacidade da infraestrutura de suportar um aumento massivo de usuários e mensagens sem perder desempenho",
            "O número de cores disponíveis na interface do usuário",
        ],
        "answer": 2,
    },
    {
        "pergunta": 'Na estrutura do Leaf Talk, qual é o papel da entidade "Logs"?',
        "opcoes": [
            "Armazenar as fotos de perfil dos usuários",
            "Registrar eventos críticos e erros do sistema para auditoria e monitoramento técnico",
            "Guardar a lista de contatos favoritos",
            "Gerenciar os emojis mais utilizados no chat",
        ],
        "answer": 1,
    },
    {
        "pergunta": "No mercado de desenvolvimento, qual é a vantagem de uma arquitetura com serviços e módulos bem separados?",
        "opcoes": [
            "Tornar o aplicativo mais pesado para o usuário final",
            "Facilitar a manutenção, permitindo atualizar uma parte do sistema sem impactar o funcionamento das outras",
            "Eliminar totalmente a necessidade de autenticação e senhas",
            "Limitar o acesso do aplicativo a apenas um usuário por vez",
        ],
        "answer": 1,
    },
]


def sample_questions():
    """Sorteia QUIZ_SIZE perguntas em ordem aleatória, SEM o gabarito."""
    idxs = random.sample(range(len(QUESTIONS)), min(QUIZ_SIZE, len(QUESTIONS)))
    return [
        {"id": i, "pergunta": QUESTIONS[i]["pergunta"], "opcoes": QUESTIONS[i]["opcoes"]}
        for i in idxs
    ]
