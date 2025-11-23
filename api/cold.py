from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# --------------------------------------------------
# Create Google Drive folder
# --------------------------------------------------

def create_folder(drive, name, parent):
    body = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent]
    }
    folder = drive.files().create(body=body, fields="id").execute()
    return folder["id"]


# --------------------------------------------------
# Send Monitoring Log
# --------------------------------------------------

def send_monitoring(automata, client, module, status, message):
    try:
        api = os.environ.get("AIRTABLE_API_KEY")
        base = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_MONITORING_TABLE")

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
        print("Monitoring error:", str(e))



# --------------------------------------------------
# COLD START – Create Central Dogma
# --------------------------------------------------

def automata_coldstart():

    try:
        root_id = os.environ.get("CENTRAL_ROOT_ID")
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

        if not root_id or not service_json:
            return {"error": "Missing environment variables"}

        info = json.loads(service_json)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        # -------------------------------
        # Create fixed folders
        # -------------------------------

        clients = create_folder(drive, "Clients", root_id)
        factures = create_folder(drive, "Factures", root_id)
        archives = create_folder(drive, "Archives", root_id)
        monitoring = create_folder(drive, "Monitoring", root_id)
        templates = create_folder(drive, "Templates", root_id)

        # Monitoring/Logs
        monitoring_logs = create_folder(drive, "Logs", monitoring)

        # -------------------------------
        # Dynamic folders (année/mois)
        # -------------------------------
        now = datetime.datetime.utcnow()
        year = str(now.year)

        mois_fr = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        # Factures/Année
        factures_year = create_folder(drive, year, factures)
        for m in mois_fr:
            create_folder(drive, m, factures_year)

        # Archives/Année
        archives_year = create_folder(drive, year, archives)
        for m in mois_fr:
            create_folder(drive, m, archives_year)

        # -------------------------------
        # Send monitoring OK
        # -------------------------------

        send_monitoring(
            automata="ColdStart",
            client="System",
            module="Python Engine – ColdStart",
            status="Succès",
            message="Central Dogma initial créé avec succès"
        )

        # -------------------------------
        # Return IDs for Airtable
        # -------------------------------

        return {
            "status": "success",

            "clients_id": clients,
            "factures_id": factures,
            "archives_id": archives,
            "monitoring_id": monitoring,
            "monitoring_logs_id": monitoring_logs,
            "templates_id": templates,

            "factures_year_id": factures_year,
            "archives_year_id": archives_year
        }

    except Exception as e:

        send_monitoring(
            automata="ColdStart",
            client="System",
            module="Python Engine – ColdStart",
            status="Erreur",
            message=str(e)
        )

        return {"status": "error", "message": str(e)}



# --------------------------------------------------
# HTTP handler
# --------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        length = int(self.headers.get("Content-Length"))
        body = self.rfile.read(length)
        data = json.loads(body.decode("utf-8"))

        trigger = data.get("trigger")

        if trigger == "cold_start":
            response = automata_coldstart()
        else:
            response = {"error": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
