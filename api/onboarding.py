from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# --------------------------------------------------
# Google Drive : création dossier
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
# Monitoring
# --------------------------------------------------
def send_monitoring(module, status, message):
    try:
        api = os.environ.get("AIRTABLE_API_KEY")
        base = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")

        url = f"https://api.airtable.com/v0/{base}/{table}"

        payload = {
            "fields": {
                "Monitoring": f"ColdStart {datetime.datetime.utcnow().isoformat()}",
                "Automata": "ColdStart",
                "Client": "SYSTEM",
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
# Cold Start — crée toute la structure centrale
# --------------------------------------------------
def cold_start():
    try:
        # GOOGLE AUTH
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        root_id = os.environ.get("CENTRAL_DOGMA_ROOT_ID")

        info = json.loads(service_json)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        now = datetime.datetime.utcnow()
        year = str(now.year)

        months = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        # -------------------------
        # 1) FACTURES
        # -------------------------
        factures = create_folder(drive, "Factures", root_id)
        year_factures = create_folder(drive, year, factures)
        for m in months:
            create_folder(drive, m, year_factures)

        # -------------------------
        # 2) ARCHIVES
        # -------------------------
        archives = create_folder(drive, "Archives", root_id)
        year_archives = create_folder(drive, year, archives)
        for m in months:
            create_folder(drive, m, year_archives)

        # -------------------------
        # 3) MONITORING / Logs
        # -------------------------
        monitoring = create_folder(drive, "Monitoring", root_id)
        logs = create_folder(drive, "Logs", monitoring)
        year_logs = create_folder(drive, year, logs)
        for m in months:
            create_folder(drive, m, year_logs)

        # -------------------------
        # 4) TEMPLATES
        # -------------------------
        templates = create_folder(drive, "Templates", root_id)
        create_folder(drive, "Factures", templates)
        create_folder(drive, "Devis", templates)
        create_folder(drive, "Contrats", templates)
        create_folder(drive, "Relances", templates)

        # -------------------------
        # SUCCESS LOG
        # -------------------------
        send_monitoring("ColdStart", "Succès", "Structure centrale créée")
        return {"status": "success"}

    except Exception as e:
        send_monitoring("ColdStart", "Erreur", str(e))
        return {"status": "error", "message": str(e)}



# --------------------------------------------------
# HTTP VERCEL
# --------------------------------------------------
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        response = cold_start()

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
