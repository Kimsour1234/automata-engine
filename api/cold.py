from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# --------------------------------------------------
# Google Drive : création dossier
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

def send_monitoring(module, status, message):
    try:
        airtable_api = os.environ.get("AIRTABLE_API_KEY")
        base_id = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")

        url = f"https://api.airtable.com/v0/{base_id}/{table}"

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
            "Authorization": f"Bearer {airtable_api}",
            "Content-Type": "application/json"
        }

        requests.post(url, json=payload, headers=headers)

    except Exception as e:
        print("Monitoring error:", e)



# --------------------------------------------------
# Cold Start – construction du Central Dogma
# --------------------------------------------------

def automata_cold_start(root_id):

    try:
        # Credentials
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        # Mois français
        months = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        now_year = str(datetime.datetime.utcnow().year)

        # --------------------------------------------------
        # 1) ARCHIVES
        # --------------------------------------------------
        archives_id = create_folder(drive, "Archives", root_id)
        archives_year = create_folder(drive, now_year, archives_id)
        for m in months:
            create_folder(drive, m, archives_year)

        # --------------------------------------------------
        # 2) FACTURES (Dynamique année/mois)
        # --------------------------------------------------
        factures_id = create_folder(drive, "Factures", root_id)
        factures_year = create_folder(drive, now_year, factures_id)
        for m in months:
            create_folder(drive, m, factures_year)

        # --------------------------------------------------
        # 3) MONITORING
        # --------------------------------------------------
        monitoring_id = create_folder(drive, "Monitoring", root_id)
        logs_id = create_folder(drive, "Logs", monitoring_id)

        # --------------------------------------------------
        # 4) TEMPLATES
        # --------------------------------------------------
        templates_id = create_folder(drive, "Templates", root_id)

        templates_factures = create_folder(drive, "Factures", templates_id)
        templates_devis = create_folder(drive, "Devis", templates_id)
        templates_contrats = create_folder(drive, "Contrats", templates_id)

        # --------------------------------------------------
        # Monitoring
        # --------------------------------------------------
        send_monitoring(
            module="ColdStart",
            status="Succès",
            message="Cold Start terminé – Central Dogma initialisé"
        )

        # --------------------------------------------------
        # Retour
        # --------------------------------------------------
        return {
            "status": "success",

            "archives_id": archives_id,
            "archives_year_id": archives_year,

            "factures_id": factures_id,
            "factures_year_id": factures_year,

            "monitoring_id": monitoring_id,
            "logs_id": logs_id,

            "templates_id": templates_id,
            "templates_factures_id": templates_factures,
            "templates_devis_id": templates_devis,
            "templates_contrats_id": templates_contrats
        }

    except Exception as e:
        send_monitoring(
            module="ColdStart",
            status="Erreur",
            message=str(e)
        )
        return {"status": "error", "message": str(e)}



# --------------------------------------------------
# Serveur HTTP Vercel
# --------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        length = int(self.headers.get("Content-Length"))
        body = self.rfile.read(length)
        data = json.loads(body.decode("utf-8"))

        trigger = data.get("trigger")

        if trigger == "cold_start":
            response = automata_cold_start(
                root_id=data.get("root_id")
            )
        else:
            response = {"error": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
