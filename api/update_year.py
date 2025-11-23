from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# --------------------------------------------------
# Helper : créer ou récupérer un dossier
# --------------------------------------------------
def get_or_create_folder(drive, parent_id, name):
    # Cherche un dossier avec ce nom dans le parent
    query = (
        f"'{parent_id}' in parents and "
        f"name = '{name}' and "
        "mimeType = 'application/vnd.google-apps.folder' and "
        "trashed = false"
    )

    results = drive.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
        pageSize=1
    ).execute()

    files = results.get("files", [])
    if files:
        # Dossier déjà existant → on le réutilise
        return files[0]["id"]

    # Sinon on le crée
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
# UPDATE YEAR – ajoute année + mois SANS doublons
# --------------------------------------------------
def automata_update_year(year_target, folders):

    try:
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not service_json:
            return {"status": "error", "message": "Missing GOOGLE_SERVICE_ACCOUNT_JSON"}

        info = json.loads(service_json)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        mois_fr = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        results = {}
        count_parents = 0

        for key, folder_id in folders.items():
            if not folder_id:
                continue  # id vide → on saute

            # 1) Année (2026) dans ce dossier
            year_folder_id = get_or_create_folder(drive, folder_id, year_target)

            # 2) 12 mois dans cette année (sans doublons)
            for m in mois_fr:
                get_or_create_folder(drive, year_folder_id, m)

            results[key] = year_folder_id
            count_parents += 1

        send_monitoring(
            "Succès",
            f"Année {year_target} appliquée sur {count_parents} dossiers dynamiques (sans doublons)."
        )

        return {
            "status": "success",
            "year": year_target,
            "updated_folders": results
        }

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

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
