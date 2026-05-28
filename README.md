# 📚 API RESTful de Gerenciamento de Livros e Tarefas Assíncronas

Esta é uma API RESTful de alto desempenho desenvolvida em Python com **FastAPI**. O projeto aplica conceitos avançados de arquitetura de software, incluindo cache em memória, processamento de tarefas em segundo plano (background jobs), mensageria distribuída e persistência de dados com ORM.

## 🚀 Tecnologias Utilizadas

*   **Framework Principal:** FastAPI (Assíncrono)
*   **Persistência de Dados:** SQLAlchemy (ORM) & SQLite
*   **Camada de Cache:** Redis
*   **Processamento Assíncrono:** Celery
*   **Mensageria e Eventos:** Apache Kafka
*   **Validação de Dados:** Pydantic
*   **Ambiente:** Docker (Suporte a Dockerfile)

## 🏗️ Diferenciais Técnicos do Projeto

*   **Estratégia de Cache (Redis):** Implementação de cache de leitura (`lista_livros`) com tempo de expiração (TTL de 30 segundos) e invalidação inteligente do cache durante operações de escrita (POST, PUT, DELETE) para garantir a consistência dos dados.
*   **Processamento em Background (Celery):** Delegação de tarefas pesadas e cálculos matemáticos (soma e fatorial) para workers em segundo plano, evitando o bloqueio da thread principal da API.
*   **Arquitetura Baseada em Eventos (Kafka):** Disparo de eventos de auditoria para um tópico do Kafka (`livros_eventos`) sempre que um novo livro é adicionado, permitindo a integração futura com outros microsserviços.
*   **Programação Assíncrona:** Uso nativo de `async/await` para otimizar a concorrência e o tempo de resposta do servidor.

## 🔀 Rotas da API

### 📖 Gerenciamento de Livros (CRUD com Cache e Mensageria)
*   `GET /livros` - Lista todos os livros ordenados por nome (Verifica o Redis antes de consultar o banco SQLite).
*   `POST /livros` - Adiciona um novo livro, salva no Redis, invalida o cache geral e envia um evento ao Kafka.
*   `PUT /livros/{id}` - Atualiza os dados de um livro existente por ID e atualiza o cache.
*   `DELETE /livros/{id}` - Remove um livro do banco de dados e limpa os registros correspondentes no Redis.
*   `GET /debug/redis` - Rota utilitária para inspecionar as chaves, valores e o TTL de tudo o que está armazenado no Redis.

### 🧮 Processamento Assíncrono (Celery + Redis)
*   `POST /calcular/soma` - Inicia uma tarefa assíncrona no Celery para somar dois números e armazena o ID no Redis.
*   `POST /calcular/fatorial` - Inicia uma tarefa assíncrona para o cálculo de fatorial.

## 🔧 Como Executar o Projeto

### Pré-requisitos
Certifique-se de ter instalado em sua máquina:
*   Python 3.10+
*   Serviço do Redis rodando (localmente ou via Docker)
*   Serviço do Apache Kafka ativo

### Passo a Passo

1. **Clone o repositório:**
   ```bash
   git clone https://github.com
   cd NOME_DO_REPOSITORIO
   ```

2. **Crie e ative o ambiente virtual:**
   ```bash
   python -m venv venv
   # No Windows:
   .\venv\Scripts\activate
   # No Linux/Mac:
   source venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Inicie o servidor do FastAPI:**
   ```bash
   fastapi dev nomearquivo.py
   ```

5. **Inicie o Worker do Celery (em outro terminal):**
   ```bash
   celery -A celery_app worker --loglevel=info
   ```

A API estará disponível para testes em `http://127.0.0.1:8000` e a documentação interativa automática estará no endpoint `/docs`.
