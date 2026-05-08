import io

def test_upload_file(client):

    file = io.BytesIO(b"conteudo teste")

    response = client.post(
        "/upload/",
        files={
            "file": (
                "teste.txt",
                file,
                "text/plain"
            )
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "url" in data
    
"""
Os testes de upload têm como objetivo validar o funcionamento correto do envio de arquivos dentro da aplicação, 
garantindo que imagens, documentos ou outros tipos de mídia sejam processados e armazenados de forma segura e eficiente. 
Durante os testes são verificadas funcionalidades relacionadas ao recebimento dos arquivos pela API, validação de formatos 
permitidos, controle de tamanho máximo e tratamento adequado de arquivos inválidos ou corrompidos. Também são analisados 
os processos de armazenamento e recuperação dos arquivos enviados, assegurando que os dados sejam salvos corretamente 
e possam ser acessados posteriormente pela aplicação. Além disso, os testes verificam possíveis cenários de erro e 
comportamentos inesperados, contribuindo para aumentar a estabilidade, segurança e confiabilidade do sistema de upload.

"""