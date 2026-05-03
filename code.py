import base64

client_id = "25aa9d9ea64249e4bb00bd2ab1073001"
client_secret = "ac21d19799874726948a559dd838d78d"

# Кодируем строку
credentials = f"{client_id}:{client_secret}"
encoded = base64.b64encode(credentials.encode()).decode()

print(encoded)
# Использование в заголовке
headers = {"Authorization": f"Basic {encoded}"}