from http.server import BaseHTTPRequestHandler
import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
from datetime import datetime

# --------------------------
# Google Drive setup
# --------------------------
def get_drive_service():
    service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)

def create_folder(drive, name, parent_id):
    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    folder = drive.files().create(body=file_metadata, fields="id").execute()
    return folder["id"]

# --------------------------
# Airtable monitoring
# --------------------------
def send_monitoring_log(module, status, message, client):
    airtable_api = os.environ["AIRTABLE_API_KEY"]
    base_id = os.environ["AIRTABLE_BASE_ID"]
    table_name = os.environ["AIRTABLE_TABLE_NAME"]

    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    headers = {"Authorization": f"Bearer {airtable_api}", "Content-Type": "application/json"}

    data = {
        "fields": {
            "automata": "Onboarding",
            "client": client,
            "type": "log",
            "statut": status,
            "module": module,
            "message": message,
            "date": datetime.now().isoformat()
        }
    }

    requests.post(url, headers=headers, json=data)


# --------------------------
# Main Automata onboarding
# --------------------------
def automata_onboarding(client_name, year):
    drive = get_drive_service()
    clients_root = os.environ["CLIENTS_ROOT_ID"]

    # 1) création du dossier client
    client_folder = create_folder(drive, client_name, clients_root)

    # Sous-dossiers principaux
    factures = create_folder(drive, "Factures", client_folder)
    docs = create_folder(drive, "Docs", client_folder)
    backups = create_folder(drive, "Backups", client_folder)
    devis = create_folder(drive, "Devis", client_folder)
    contrats = create_folder(drive, "Contrats", client_folder)

    # Factures → année → mois
    year_folder = create_folder(drive, str(year), factures)
    for month in ["01-Janvier","02-Février","03-Mars","04-Avril","05-Mai","06-Juin",
                  "07-Juillet","08-Août","09-Septembre","10-Octobre","11-Novembre","12-Décembre"]:
        create_folder(drive, month, year_folder)

    # Docs/Relances → année → r1/r2/r3
    relances = create_folder(drive, "Relances", docs)
    rel_year = create_folder(drive, str(year), relances)
    create_folder(drive, "R1", rel_year)
    create_folder(drive, "R2", rel_year)
    create_folder(drive, "R3", rel_year)

    # Devis → année → mois
    devis_year = create_folder(drive, str(year), devis)
    for month in ["01-Janvier","02-Février","03-Mars","04-Avril","05-Mai","06-Juin",
                  "07-Juillet","08-Août","09-Septembre","10-Octobre","11-Novembre","12-Décembre"]:
        create_folder(drive, month, devis_year)

    # Contrats → année → mois
    contrats_year = create_folder(drive, str(year), contrats)
    for month in ["01-Janvier","02-Février","03-Mars","04-Avril","05-Mai","06-Juin",
                  "07-Juillet","08-Août","09-Septembre","10-Octobre","11-Novembre","12-Décembre"]:
        create_folder(drive, month, contrats_year)

    send_monitoring_log("onboarding", "success", "Dossiers créés", client_name)

    return {
        "client_folder_id": client_folder,
        "status": "completed"
    }


# --------------------------
# HTTP Handler
# --------------------------
class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers.get('Content-Length'))
        body = self.rfile.read(length)
        data = json.loads(body.decode("utf-8"))

        client_name = data.get("client_name")
        year = int(data.get("year", 2025))
        trigger = data.get("trigger", "create_folders")

        if trigger == "create_folders":
            result = automata_onboarding(client_name, year)
        else:
            result = {"error": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode("utf-8"))
