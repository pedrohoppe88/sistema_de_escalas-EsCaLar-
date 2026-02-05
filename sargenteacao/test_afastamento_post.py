import requests

# URL da API
url = 'http://127.0.0.1:8000/api/afastamentos/'

# Dados do afastamento a ser criado
data = {
    "militar": 1,
    "tipo": "FERIAS",
    "data_inicio": "2026-02-01",
    "data_fim": "2026-02-10",
    "observacoes": "Férias regulamentares"
}

# Fazendo o POST
response = requests.post(url, json=data)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")

# Testando GET para ver se foi criado
get_response = requests.get(url)
print(f"GET Status: {get_response.status_code}")
print(f"Afastamentos: {get_response.json()}")
