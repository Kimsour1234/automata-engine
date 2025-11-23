from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# --------------------------------------------------
# Google Drive : création de dossier
# --------------------------------------------------

def create_folder(drive, name, parent_id):
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    f = drive.files().create(body=metadata, fields="id").execute()
    return f["id"]


# --------------------------------------------------
# Monitoring Airtable
# --------------------------------------------------

def send_monitoring(module, status, message):
    try:
        api = os.environ.get("AIRTABLE_API_KEY")
        base = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")

        url = f"https://api.airtable.com/v0/{base}/{table}"

        payload = {
            "fields": {
                "Monitoring": f"Log ColdStart {datetime.datetime.utcnow().isoformat()}",
                "Automata": "ColdStart",
                "Client": "Central System",
                "Type": "Log",
                "Statut": status,
                "Module": module,
                "Message": message,
                "Date": datetime.datetime.utcnow().isoformat() + "Z"
            }
        }

        headers = {
            "Authorization": f"Bearer {api}",
            "Content-Type": "application/json"
        }

        requests.post(url, json=payload, headers=headers)

    except Exception as e:
        print("Monitoring error:", e)



# --------------------------------------------------
# Cold & Dark (création des dossiers du Central Dogma)
# --------------------------------------------------

def automata_coldstart():
    try:
        root_id = os.environ.get("CENTRAL_DOGMA_ROOT_ID")
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

        if not root_id or not service_json:
            return {"status": "error", "message": "Missing env variables"}

        info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        drive = build("drive", "v3", credentials=creds)

        # Mois FR
        months = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        year = str(datetime.datetime.utcnow().year)

        # --- Dossiers fixes ---
        factures = create_folder(drive, "Factures", root_id)
        archives = create_folder(drive, "Archives", root_id)
        monitoring = create_folder(drive, "Monitoring", root_id)
        logs = create_folder(drive, "Logs", monitoring)

        # --- Dossiers dynamiques ---
        factures_year = create_folder(drive, year, factures)
        archives_year = create_folder(drive, year, archives)
        logs_year = create_folder(drive, year, logs)

        for m in months:
            create_folder(drive, m, factures_year)
            create_folder(drive, m, archives_year)
            create_folder(drive, m, logs_year)

        send_monitoring(
            module="Python ColdStart",
            status="Succès",
            message="Central Dogma initialisé avec succès"
        )

        return {"status": "success"}

    except Exception as e:

        send_monitoring(
            module="Python ColdStart",
            status="Erreur",
            message=str(e)
        )

        return {"status": "error", "message": str(e)}



# --------------------------------------------------
# Serveur HTTP
# --------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers.get("Content-Length"))
        body = self.rfile.read(length)
        data = json.loads(body.decode("utf-8"))

        trigger = data.get("trigger")

        if trigger == "cold":
            response = automata_coldstart()
        else:
            response = {"status": "error", "message": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
