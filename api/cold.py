from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# --------------------------------------------------
# Google Drive – création de dossier
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
        airtable_api = os.environ.get("AIRTABLE_API_KEY")
        base_id = os.environ.get("AIRTABLE_BASE_ID")
        table_name = os.environ.get("AIRTABLE_TABLE_NAME")

        url = f"https://api.airtable.com/v0/{base_id}/{table_name}"

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
            "Authorization": f"Bearer {airtable_api}",
            "Content-Type": "application/json"
        }

        requests.post(url, json=payload, headers=headers)

    except Exception as e:
        print("Monitoring error:", e)


# --------------------------------------------------
# Lecture Airtable : table "Cold" (IDs racine)
# --------------------------------------------------

def load_root_ids():
    airtable_api = os.environ.get("AIRTABLE_API_KEY")
    base_id = os.environ.get("AIRTABLE_BASE_ID")
    central_table = os.environ.get("AIRTABLE_CENTRAL_TABLE")  # Doit être "Cold"

    url = f"https://api.airtable.com/v0/{base_id}/{central_table}"

    headers = {
        "Authorization": f"Bearer {airtable_api}",
        "Content-Type": "application/json"
    }

    resp = requests.get(url, headers=headers)
    data = resp.json()

    # On prend la première ligne de la table Cold
    record = data["records"][0]["fields"]

    return {
        "archives": record["archives_root_id"],
        "factures": record["factures_root_id"],
        "monitoring": record["monitoring_root_id"],
        "relances": record["relances_root_id"]
    }


# --------------------------------------------------
# Cold & Dark – création de la structure dynamique
# --------------------------------------------------

def cold_and_dark():
    try:
        # 1) Charger les IDs racine depuis la table Cold
        roots = load_root_ids()

        archives_root = roots["archives"]
        factures_root = roots["factures"]
        monitoring_root = roots["monitoring"]
        relances_root = roots["relances"]

        # 2) Auth Google
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        service_info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            service_info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        # 3) Année + mois
        year = str(datetime.datetime.utcnow().year)

        months = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        # -----------------------------------
        # FACTURES / année / 12 mois
        # -----------------------------------
        year_factures = create_folder(drive, year, factures_root)
        for m in months:
            create_folder(drive, m, year_factures)

        # -----------------------------------
        # ARCHIVES / année / 12 mois
        # -----------------------------------
        year_archives = create_folder(drive, year, archives_root)
        for m in months:
            create_folder(drive, m, year_archives)

        # -----------------------------------
        # MONITORING / Logs / année / 12 mois
        # -----------------------------------
        logs_root = create_folder(drive, "Logs", monitoring_root)
        year_logs = create_folder(drive, year, logs_root)
        for m in months:
            create_folder(drive, m, year_logs)

        # -----------------------------------
        # RELANCES / R1 / R2 / R3 (pas d'année)
        # -----------------------------------
        create_folder(drive, "R1", relances_root)
        create_folder(drive, "R2", relances_root)
        create_folder(drive, "R3", relances_root)

        # Monitoring OK
        send_monitoring(
            module="Python Cold & Dark",
            status="Succès",
            message=f"Structure dynamique créée pour l'année {year}"
        )

        return {
            "status": "success",
            "year": year
        }

    except Exception as e:
        send_monitoring(
            module="Python Cold & Dark",
            status="Erreur",
            message=str(e)
        )
        return {
            "status": "error",
            "message": str(e)
        }


# --------------------------------------------------
# Serveur HTTP Vercel
# --------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        response = cold_and_dark()

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
