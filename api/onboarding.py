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
        table = os.environ.get("AIRTABLE_TABLE_NAME")  # <- IMPORTANT : ton .env

        url = f"https://api.airtable.com/v0/{base_id}/{table}"

        payload = {
            "fields": {
                "Automata": automata,
                "Client": client,
                "Type": "Log",
                "Statut": status,
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

def automata_onboarding(client_name):

    try:
        # Lecture des variables Vercel
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        clients_root = os.environ.get("CLIENTS_ROOT_ID")

        if not service_json or not clients_root:
            return {"error": "Missing environment variables"}

        # Authentification Google
        service_info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            service_info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        drive = build("drive", "v3", credentials=creds)

        # Date dynamique
        now = datetime.datetime.utcnow()
        year_str = str(now.year)
        month_str = now.strftime("%m-%B")   # ex: 11-Novembre

        # ----------------------------
        # 1) Dossier Client
        # ----------------------------
        client_folder = create_folder(drive, client_name, clients_root)

        # ----------------------------
        # 2) FACTURES
        # ----------------------------
        factures = create_folder(drive, "Factures", client_folder)
        factures_year = create_folder(drive, year_str, factures)
        create_folder(drive, month_str, factures_year)

        # ----------------------------
        # 3) BACKUPS
        # ----------------------------
        backups = create_folder(drive, "Backups", client_folder)

        # Backups / Factures
        backup_factures = create_folder(drive, "Factures", backups)
        backup_factures_year = create_folder(drive, year_str, backup_factures)
        create_folder(drive, month_str, backup_factures_year)

        # Backups / Relances
        backup_relances = create_folder(drive, "Relances", backups)
        backup_relances_year = create_folder(drive, year_str, backup_relances)
        create_folder(drive, month_str, backup_relances_year)

        # ----------------------------
        # 4) DEVIS
        # ----------------------------
        devis = create_folder(drive, "Devis", client_folder)
        devis_year = create_folder(drive, year_str, devis)
        create_folder(drive, month_str, devis_year)

        # ----------------------------
        # 5) DOCS → RELANCES (R1/R2/R3)
        # ----------------------------
        docs = create_folder(drive, "Docs", client_folder)
        docs_relances = create_folder(drive, "Relances", docs)

        for r in ["R1", "R2", "R3"]:
            create_folder(drive, r, docs_relances)

        # ----------------------------
        # 6) CONTRATS
        # ----------------------------
        contrats = create_folder(drive, "Contrats", client_folder)
        contrats_year = create_folder(drive, year_str, contrats)
        create_folder(drive, month_str, contrats_year)

        # ----------------------------
        # Monitoring Succès
        # ----------------------------
        send_monitoring(
            automata="Onboarding",
            client=client_name,
            module="Python Engine - Onboarding",
            status="Succès",
            message=f"Onboarding complet pour {client_name}"
        )

        return {
            "status": "success",
            "client_folder": client_folder
        }

    except Exception as e:

        # Monitoring Erreur
        send_monitoring(
            automata="Onboarding",
            client=client_name,
            module="Python Engine - Onboarding",
            status="Erreur",
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
        trigger = data.get("trigger", "create_folders")

        if trigger == "create_folders":
            response = automata_onboarding(client_name)
        else:
            response = {"error": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
