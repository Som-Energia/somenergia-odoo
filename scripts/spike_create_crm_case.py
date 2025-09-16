import json
import requests
from pathlib import Path

# --- Carregar configuració des de config.json ---
CONFIG_FILE = Path(__file__).parent / "config.json"

if not CONFIG_FILE.exists():
    raise FileNotFoundError(f"No s'ha trobat {CONFIG_FILE}. Crea'l amb les dades d'Odoo.")

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    cfg = json.load(f)

odoo_url = cfg["odoo_url"]
db = cfg["db"]
username = cfg["username"]
password = cfg["password"]

# --- Autenticació ---
session = requests.Session()  # Guardarà automàticament les cookies

auth_response = session.post(
    f"{odoo_url}/web/session/authenticate",
    json={
        "jsonrpc": "2.0",
        "params": {
            "db": db,
            "login": username,
            "password": password
        }
    }
).json()

if auth_response.get("error"):
    raise Exception(f"Error d'autenticació: {auth_response['error']}")

uid = auth_response["result"]["uid"]

# --- Funció per crear un cas CRM ---
def crear_cas_crm(nom, telefon=None, email=None, descripcio=None):
    data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "crm.lead",
            "method": "create",
            "args": [{
                "name": nom,
                "contact_name": nom,
                "phone": telefon,
                "email_from": email,
                "description": descripcio,
                "type": "opportunity"
            }],
            "kwargs": {},
        },
        "id": uid
    }

    resp = session.post(  # session porta ja la cookie
        f"{odoo_url}/web/dataset/call_kw",
        json=data
    ).json()

    if resp.get("error"):
        raise Exception(f"Error en crear el CRM: {resp['error']}")

    return resp["result"]

# --- Exemple d'ús ---
if __name__ == "__main__":
    nou_id = crear_cas_crm(
        nom="Pep Garcia",
        telefon="+34999999999",
        email="pep@example.com",
        descripcio="Incidència reportada des del formulari web"
    )
    print(f"Cas CRM creat amb ID {nou_id}")
