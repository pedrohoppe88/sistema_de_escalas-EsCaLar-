# Usar imagem oficial do Python
FROM python:3.11-slim

# Definir diretório de trabalho na imagem
WORKDIR /app

# Variáveis de ambiente para otimizar o Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o projeto para dentro do container
COPY . .

# Mudar para a pasta onde está o manage.py e definir o comando padrão
WORKDIR /app/sargenteacao
CMD ["python", "manage.py", "runserver", "localhost:8000"]