from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests

# --------------------------------------------------
# FONCTION : Créer un dossier
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

def send_monitoring(module, status, message):
    try:
        api = os.environ.get("AIRTABLE_API_KEY")
        base = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")

        url = f"https://api.airtable.com/v0/{base}/{table}"

        payload = {
            "fields": {
                "Monitoring": f"Log {datetime.datetime.utcnow().isoformat()}",
                "Automata": "ColdStart",
                "Client": "-",
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
# Automata – Cold & Start
# --------------------------------------------------

def automata_coldstart():

    try:
        # ENV
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        central_root = os.environ.get("CENTRAL_ROOT_ID")
        clients_root = os.environ.get("CLIENTS_ROOT_ID")

        if not service_json or not central_root or not clients_root:
            return {"error": "Missing environment variables"}

        # AUTH
        info = json.loads(service_json)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        # Année + mois
        now = datetime.datetime.utcnow()
        year_str = str(now.year)

        mois_fr = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        # --------------------------------------------------
        # 1) CENTRAL ROOT – Factures
        # --------------------------------------------------
        central_factures = create_folder(drive, "Factures", central_root)
        central_factures_year = create_folder(drive, year_str, central_factures)
        for m in mois_fr:
            create_folder(drive, m, central_factures_year)

        # --------------------------------------------------
        # 2) CENTRAL ROOT – Archives
        # --------------------------------------------------
        central_archives = create_folder(drive, "Archives", central_root)
        central_archives_year = create_folder(drive, year_str, central_archives)
        for m in mois_fr:
            create_folder(drive, m, central_archives_year)

        # --------------------------------------------------
        # 3) CENTRAL ROOT – Monitoring / Logs
        # --------------------------------------------------
        monitoring = create_folder(drive, "Monitoring", central_root)
        monitoring_logs = create_folder(drive, "Logs", monitoring)
        monitoring_year = create_folder(drive, year_str, monitoring_logs)
        for m in mois_fr:
            create_folder(drive, m, monitoring_year)

        # --------------------------------------------------
        # Monitoring OK
        # --------------------------------------------------
        send_monitoring(
            module="ColdStart",
            status="Succès",
            message="Cold & Start terminé avec succès (central root)"
        )

        return {
            "status": "success",
            "central_factures_id": central_factures,
            "central_archives_id": central_archives,
            "central_monitoring_logs_id": monitoring_logs
        }

    except Exception as e:
        send_monitoring(
            module="ColdStart",
            status="Erreur",
            message=str(e)
        )
        return {"error": str(e)}


# --------------------------------------------------
# Serveur HTTP Vercel
# --------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        length = int(self.headers.get("Content-Length"))
        body = self.rfile.read(length)
        data = json.loads(body.decode("utf-8"))

        trigger = data.get("trigger")

        if trigger == "coldstart":
            response = automata_coldstart()
        else:
            response = {"error": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
