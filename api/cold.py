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
        api = os.environ.get("AIRTABLE_API_KEY")
        base = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")

        url = f"https://api.airtable.com/v0/{base}/{table}"

        payload = {
            "fields": {
                "Monitoring": f"Log {datetime.datetime.utcnow().isoformat()}",
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
            "Authorization": f"Bearer {api}",
            "Content-Type": "application/json"
        }

        requests.post(url, json=payload, headers=headers)

    except Exception as e:
        print("Monitoring error:", e)



# --------------------------------------------------
# Cold Start – Création des dossiers dynamiques
# --------------------------------------------------

def cold_start(root_id):

    try:
        # Google Auth
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        # Dossiers fixes
        archives = create_folder(drive, "Archives", root_id)
        factures = create_folder(drive, "Factures", root_id)
        monitoring = create_folder(drive, "Monitoring", root_id)
        logs = create_folder(drive, "Logs", monitoring)

        # Année + Mois
        now = datetime.datetime.utcnow()
        year = str(now.year)

        mois_fr = [
            "01-Janvier","02-Février","03-Mars","04-Avril",
            "05-Mai","06-Juin","07-Juillet","08-Août",
            "09-Septembre","10-Octobre","11-Novembre","12-Décembre"
        ]

        # Archives dynamique
        arch_year = create_folder(drive, year, archives)
        for m in mois_fr:
            create_folder(drive, m, arch_year)

        # Factures dynamique
        fac_year = create_folder(drive, year, factures)
        for m in mois_fr:
            create_folder(drive, m, fac_year)

        # Monitoring dynamique
        log_year = create_folder(drive, year, logs)
        for m in mois_fr:
            create_folder(drive, m, log_year)

        # Monitoring OK
        send_monitoring(
            automata="ColdStart",
            client="SYSTEM",
            module="Python Engine - ColdStart",
            status="Succès",
            message="Dossiers généraux créés"
        )

        return {"status": "success"}

    except Exception as e:

        send_monitoring(
            automata="ColdStart",
            client="SYSTEM",
            module="Python Engine - ColdStart",
            status="Erreur",
            message=str(e)
        )

        return {"status": "error", "message": str(e)}



# --------------------------------------------------
# Handler HTTP
# --------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers.get("Content-Length"))
        body = self.rfile.read(length)
        data = json.loads(body.decode("utf-8"))

        trigger = data.get("trigger")

        if trigger == "cold":
            response = cold_start(os.environ.get("CENTRAL_ROOT_ID"))
        else:
            response = {"error": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
