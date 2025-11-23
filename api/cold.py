from http.server import BaseHTTPRequestHandler
import json, os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime
import requests


# --------------------------------------------------
# Google Drive — création de dossier
# --------------------------------------------------

def create_folder(drive, name, parent_id):
    body = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    folder = drive.files().create(body=body, fields="id").execute()
    return folder["id"]


# --------------------------------------------------
# Monitoring Airtable
# --------------------------------------------------

def send_monitoring(status, message):
    try:
        api = os.environ.get("AIRTABLE_API_KEY")
        base = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")

        url = f"https://api.airtable.com/v0/{base}/{table}"

        payload = {
            "fields": {
                "Monitoring": f"ColdStart {datetime.datetime.utcnow().isoformat()}",
                "Automata": "ColdStart",
                "Client": "System",
                "Type": "Log",
                "Statut": status,
                "Module": "Python Engine – ColdStart",
                "Message": message,
                "Date": datetime.datetime.utcnow().isoformat() + "Z"
            }
        }

        headers = {
            "Authorization": f"Bearer {api}",
            "Content-Type": "application/json"
        }

        requests.post(url, json=payload, headers=headers)

    except:
        pass



# --------------------------------------------------
# Automata Cold & Dark (provisoire)
# --------------------------------------------------

def automata_cold_start():

    try:
        # Credentials
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        root_id = os.environ.get("CENTRAL_ROOT_ID")   # IMPORTANT

        if not service_json or not root_id:
            return {"error": "Missing environment variables"}

        info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        # -------------------------------------
        # ▼ Création des dossiers fixes
        # -------------------------------------

        archives = create_folder(drive, "Archives", root_id)
        factures = create_folder(drive, "Factures", root_id)
        monitoring = create_folder(drive, "Monitoring", root_id)
        relances = create_folder(drive, "Relances", root_id)
        templates = create_folder(drive, "Templates", root_id)

        # Monitoring dossier interne
        logs = create_folder(drive, "Logs", monitoring)

        # Retour API
        send_monitoring(
            status="Succès",
            message="Cold & Dark provisoire OK — dossiers fixes créés"
        )

        return {
            "status": "success",
            "root": root_id,
            "archives": archives,
            "factures": factures,
            "monitoring": monitoring,
            "logs": logs,
            "relances": relances,
            "templates": templates
        }

    except Exception as e:

        send_monitoring(
            status="Erreur",
            message=str(e)
        )

        return {"status": "error", "message": str(e)}



# --------------------------------------------------
# Server HTTP (Vercel)
# --------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        response = automata_cold_start()

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
