from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# --------------------------------------------------
# Google Drive – create a folder
# --------------------------------------------------

def create_folder(drive, name, parent_id):
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    folder = drive.files().create(body=metadata, fields="id").execute()
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
                "Monitoring": f"Log Cold&Dark {datetime.datetime.utcnow().isoformat()}",
                "Automata": "ColdAndDark",
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
# Lecture Airtable pour récupérer les IDs racine
# --------------------------------------------------

def load_root_ids():
    api = os.environ.get("AIRTABLE_API_KEY")
    base = os.environ.get("AIRTABLE_BASE_ID")
    table = os.environ.get("AIRTABLE_CENTRAL_TABLE")  # ⚠️ Nouvelle variable !!

    url = f"https://api.airtable.com/v0/{base}/{table}"

    headers = {
        "Authorization": f"Bearer {api}",
        "Content-Type": "application/json"
    }

    r = requests.get(url, headers=headers).json()

    record = r["records"][0]["fields"]

    return {
        "archives": record["archives_root_id"],
        "factures": record["factures_root_id"],
        "monitoring": record["monitoring_root_id"],
        "relances": record["relances_root_id"]
    }



# --------------------------------------------------
# COLD & DARK – structure complète
# --------------------------------------------------

def cold_and_dark():
    try:
        # --- Load root IDs from Airtable ---
        roots = load_root_ids()

        archives_root = roots["archives"]
        factures_root = roots["factures"]
        monitoring_root = roots["monitoring"]
        relances_root = roots["relances"]

        # --- Prepare Google Drive ---
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        drive = build("drive", "v3", credentials=creds)

        # Months
        months = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        year = str(datetime.datetime.utcnow().year)

        # -------------------------------
        # FACTURES / year / months
        # -------------------------------
        y_fact = create_folder(drive, year, factures_root)
        for m in months:
            create_folder(drive, m, y_fact)

        # -------------------------------
        # ARCHIVES / year / months
        # -------------------------------
        y_arc = create_folder(drive, year, archives_root)
        for m in months:
            create_folder(drive, m, y_arc)

        # -------------------------------
        # MONITORING / Logs / year / months
        # -------------------------------
        logs = create_folder(drive, "Logs", monitoring_root)
        y_mon = create_folder(drive, year, logs)
        for m in months:
            create_folder(drive, m, y_mon)

        # -------------------------------
        # RELANCES / R1/R2/R3
        # -------------------------------
        create_folder(drive, "R1", relances_root)
        create_folder(drive, "R2", relances_root)
        create_folder(drive, "R3", relances_root)

        # Monitoring OK
        send_monitoring(
            module="Python Cold & Dark",
            status="Succès",
            message="Structure Cold & Dark générée avec succès"
        )

        return {"status": "success"}

    except Exception as e:

        send_monitoring(
            module="Python Cold & Dark",
            status="Erreur",
            message=str(e)
        )
        return {"status": "error", "message": str(e)}



# --------------------------------------------------
# HTTP Handler
# --------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        response = cold_and_dark()

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
