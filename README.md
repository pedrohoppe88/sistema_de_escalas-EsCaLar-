# Sistema de Sargenteação

Sistema de gestão militar para controle de serviços, efetivos e afastamentos da troops.

## 📋 Índice

- [Sobre o Projeto](#sobre-o-projeto)
- [Funcionalidades](#funcionalidades)
- [Tecnologias](#tecnologias)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [API REST](#api-rest)
- [Testes](#testes)
- [Docker](#docker)
- [Contribuição](#contribuição)
- [Licença](#licença)

---

## 📖 Sobre o Projeto

O Sistema de Sargenteação é uma aplicação web desenvolvida em Django para automatizar e gerenciar os serviços militares, controle de efetivo diário e registros de afastamento de militares.

## ✨ Funcionalidades

### Gestão de Militares
- Cadastro de militares com informações de graduação e subunidade
- Controle de militares ativos/inativos
- Histórico completo de serviços por militar

### Registro de Serviços
- Registro de diversos tipos de serviço:
  - Guarda ao Quartel
  - Plantão
  - Permanência
  - Comandante da Guarda
  - Cabo da Guarda
  - Cabo de Dia
  - Adjunto
  - Oficial de Dia
  - Sargento de Dia
  - Motorista de Dia
- Validação automática para evitar conflito com afastamentos
- Controle de funções especiais por dia

### Gestão de Afastamentos
- Registro de afastamentos (Férias, Licença, Dispensa, Dispensa Médica)
- Período de início e fim
- Observações adicionais

### Dashboard e Estatísticas
- Visualização do efetivo do dia
- Estatísticas de serviços por período
- Histórico detalhado por militar

### API REST
- Endpoints para integração com outros sistemas
- Autenticação JWT (JSON Web Token)
- Serializers para Militar, Afastamento e Serviço

### Relatórios
- Geração de relatórios em PDF
- Aditamentos de serviço

---

## 🛠 Tecnologias

- **Backend**: Django 5.2
- **API**: Django REST Framework
- **Autenticação**: Django REST Framework SimpleJWT
- **PDF**: ReportLab
- **Containerização**: Docker & Docker Compose
- **Banco de Dados**: SQLite (desenvolvimento) / PostgreSQL (produção)

---

## 📦 Pré-requisitos

- Python 3.10+
- Docker e Docker Compose
- Git

---

## 🚀 Instalação

### 1. Clone o repositório

```
bash
git clone <url-do-repositorio>
cd sistema_sargenteacao
```

### 2. Configure o ambiente virtual (sem Docker)

```
bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Instale as dependências

```
bash
pip install -r requirements.txt
```

---

## ⚙️ Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```
env
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Banco de dados (opcional - usa SQLite por padrão)
DATABASE_NAME=db.sqlite3

# JWT Settings
JWT_SECRET_KEY=sua-jwt-secret-key
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=1440
```

### Migrações do Banco de Dados

```
bash
cd sargenteacao
python manage.py migrate
```

### Criar Superusuário

```
bash
python manage.py createsuperuser
```

---

## ▶️ Uso

### Executar o Servidor de Desenvolvimento

```
bash
cd sargenteacao
python manage.py runserver
```

Acesse: http://127.0.0.1:8000/

### Interface Administrativa

Acesse: http://127.0.0.1:8000/admin/

---

## 🌐 API REST

### Autenticação

Obter token de acesso:

```
bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "seu-usuario", "password": "sua-senha"}'
```

Resposta:
```
json
{
  "access": "token-de-acesso",
  "refresh": "token-de-refresh"
}
```

### Endpoints Disponíveis

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/militares/` | Listar militares |
| POST | `/api/militares/` | Criar militar |
| GET | `/api/servicos/` | Listar serviços |
| POST | `/api/servicos/` | Criar serviço |
| GET | `/api/afastamentos/` | Listar afastamentos |
| POST | `/api/afastamentos/` | Criar afastamento |
| GET | `/api/efetivo/` | Efetivo do dia |

### Usando o Token

```
bash
curl -X GET http://127.0.0.1:8000/api/militares/ \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

---

## 🧪 Testes

### Executar Todos os Testes

```
bash
cd sargenteacao
python manage.py test
```

### Executar Testes Específicos

```bash
python manage.py test core.tests.test_login
python manage.py test core.tests.test_api
```

---

## 🐳 Docker

### Construir e Executar com Docker Compose

```
bash
docker-compose up --build
```

### Serviços Disponíveis

- **Web**: Aplicação Django na porta 8000
- **Banco de Dados**: SQLite (embutido no container)

### Acessar o Container

```
bash
docker-compose exec web bash
```

### Executar Migrações no Container

```
bash
docker-compose exec web python manage.py migrate
```

### Criar Superusuário no Container

```
bash
docker-compose exec web python manage.py createsuperuser
```

---

## 📁 Estrutura do Projeto

```
sistema_sargenteacao/
├── sargenteacao/           # Projeto Django
│   ├── core/               # Aplicação principal
│   │   ├── models.py       # Modelos do banco de dados
│   │   ├── views.py        # Views
│   │   ├── urls.py         # Rotas
│   │   ├── serializers/    # Serializers da API
│   │   ├── templates/      # Templates HTML
│   │   ├── tests/          # Testes
│   │   ├── services.py     # Lógica de negócio
│   │   └── pdf_services.py # Geração de PDF
│   └── sargenteacao/       # Configurações do projeto
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

---

## 📞 Suporte

Para dúvidas e suporte, entre em contato através das issues do GitHub.

---

Desenvolvido com ❤️ para gestão militar.
