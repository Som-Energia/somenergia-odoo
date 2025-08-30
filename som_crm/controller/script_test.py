import http.client

conn = http.client.HTTPConnection("localhost:8069")

payload = "{\n\t\"name\": \"Oportunidad importante\",\n\t\"contact_name\": \"María García\",\n\t\"email\": \"maria@empresa.com\",\n\t\"phone\": \"+34 600 123 456\",\n\t\"description\": \"Interesada en servicios de consultoría\"\n}"

headers = {
    'cookie': "frontend_lang=en_US; session_id=f3138abe4e71f8a6e52678ea7e20198066cefe4f",
    'Content-Type': "application/json",
    'User-Agent': "insomnia/11.5.0",
    'X-API-Key': "change_this_default_api_key_123"
    }

conn.request("POST", "/api/crm/lead", payload, headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))
