from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# --------------------------------------------------
# Google Drive : création de dossier
# --------------------------------------------------

def create_folder(drive, name, parent_id):
    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    folder = drive.files().create(body=file_metadata, fields="id").execute()
    return folder["id"]


# --------------------------------------------------
# Monitoring Airtable
# --------------------------------------------------

def send_monitoring(automata, client, module, status, message):
    try:
        airtable_api = os.environ.get("AIRTABLE_API_KEY")
        base_id = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")

        url = f"https://api.airtable.com/v0/{base_id}/{table}"

        payload = {
            "fields": {
                "Automata": automata,
                "Client": client,
                "Type": "Log",
                "Statut": status,   # "Succès" ou "Erreur"
                "Module": module,
                "Message": message,
                "Date": datetime.datetime.utcnow().isoformat() + "Z"
            }
        }

        headers = {
            "Authorization": f"Bearer {airtable_api}",
            "Content-Type": "application/json"
        }

        requests.post(url, json=payload, headers=headers)

    except Exception as e:
        print("Monitoring error:", e)


# --------------------------------------------------
# Automata Onboarding
# --------------------------------------------------

def automata_onboarding(client_name, year):
    try:
        # Lire variables Vercel
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        clients_root = os.environ.get("CLIENTS_ROOT_ID")

        if not service_json or not clients_root:
            return {"error": "Missing environment variables"}

        service_info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            service_info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        drive = build("drive", "v3", credentials=creds)

        # ----------------------------
        # 1) Création dossier client
        # ----------------------------
        client_folder = create_folder(drive, client_name, clients_root)

        # ----------------------------
        # 2) Sous-dossiers principaux
        # ----------------------------
        factures = create_folder(drive, "Factures", client_folder)
        docs = create_folder(drive, "Docs", client_folder)
        backups = create_folder(drive, "Backups", client_folder)
        devis = create_folder(drive, "Devis", client_folder)
        contrats = create_folder(drive, "Contrats", client_folder)

        # ----------------------------
        # 3) ANNÉE + MOIS (Factures)
        # ----------------------------
        year_folder = create_folder(drive, str(year), factures)

        months = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        for m in months:
            create_folder(drive, m, year_folder)

        # ----------------------------
        # 4) Relances R1 / R2 / R3
        # ----------------------------
        relances = create_folder(drive, "Relances", docs)
        year_relances = create_folder(drive, str(year), relances)

        for r in ["R1", "R2", "R3"]:
            create_folder(drive, r, year_relances)

        # ----------------------------
        # Monitoring
        # ----------------------------

        send_monitoring(
            automata="autodossier",
            client=client_name,
            module="google drive",
            status="success",
            message="Onboarding complet OK"
        )

        return {
            "status": "success",
            "client_folder": client_folder
        }

    except Exception as e:
        send_monitoring(
            automata="autodossier",
            client=client_name,
            module="google drive",
            status="error",
            message=str(e)
        )
        return {"status": "error", "message": str(e)}


# --------------------------------------------------
# Serveur HTTP Vercel
# --------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers.get("Content-Length"))
        body = self.rfile.read(length)
        data = json.loads(body.decode("utf-8"))

        client_name = data.get("client_name")
        year = int(data.get("year", 2025))
        trigger = data.get("trigger", "create_folders")

        if trigger == "create_folders":
            response = automata_onboarding(client_name, year)
        else:
            response = {"error": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
