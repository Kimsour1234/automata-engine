from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests

# --------------------------------------------------
# Create folder
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
def send_monitoring(status, message):
    try:
        api = os.environ.get("AIRTABLE_API_KEY")
        base = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")

        url = f"https://api.airtable.com/v0/{base}/{table}"

        payload = {
            "fields": {
                "Monitoring": f"Log {datetime.datetime.utcnow().isoformat()}",
                "Automata": "UpdateYear",
                "Client": "-",
                "Type": "Log",
                "Statut": status,
                "Module": "Python - UpdateYear",
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
# UPDATE YEAR – Apply year + months to 12 folders
# --------------------------------------------------
def automata_update_year(year_target, folders):

    try:
        # Init Google
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        info = json.loads(service_json)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        # Months
        mois_fr = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        # For each dynamic folder
        results = {}

        for key, folder_id in folders.items():

            if folder_id is None or folder_id == "":
                continue

            # Create YEAR inside this folder
            year_folder = create_folder(drive, year_target, folder_id)

            # Create 12 months
            for m in mois_fr:
                create_folder(drive, m, year_folder)

            results[key] = year_folder

        # Monitoring OK
        send_monitoring("Succès", f"Année {year_target} ajoutée dans 12 dossiers.")

        return {"status": "success", "year": year_target, "created": results}

    except Exception as e:
        send_monitoring("Erreur", str(e))
        return {"status": "error", "message": str(e)}



# --------------------------------------------------
# HTTP SERVER
# --------------------------------------------------
class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        length = int(self.headers.get("Content-Length"))
        data = json.loads(self.rfile.read(length).decode("utf-8"))

        trigger = data.get("trigger")

        if trigger == "update_year":

            # Build dict of the 12 dynamic folders
            folders = {
                "factures_root_id": data.get("factures_root_id"),
                "archives_root_id": data.get("archives_root_id"),
                "monitoring_root_id": data.get("monitoring_root_id"),

                "factures_folder_id_python": data.get("factures_folder_id_python"),
                "backups_factures_folder_id_python": data.get("backups_factures_folder_id_python"),
                "backups_relances_folder_id_python": data.get("backups_relances_folder_id_python"),
                "devis_folder_id_python": data.get("devis_folder_id_python"),
                "contrats_folder_id_python": data.get("contrats_folder_id_python"),
                "docs_relances_folder_id_python": data.get("docs_relances_folder_id_python"),
                "R1_folder_id_python": data.get("R1_folder_id_python"),
                "R2_folder_id_python": data.get("R2_folder_id_python"),
                "R3_folder_id_python": data.get("R3_folder_id_python")
            }

            response = automata_update_year(
                year_target=data.get("year"),
                folders=folders
            )

        else:
            response = {"error": "Unknown trigger"}

        # Return HTTP response
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
