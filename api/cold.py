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
        airtable_api = os.environ.get("AIRTABLE_API_KEY")
        base_id = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")

        url = f"https://api.airtable.com/v0/{base_id}/{table}"

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
            "Authorization": f"Bearer {airtable_api}",
            "Content-Type": "application/json"
        }

        r = requests.post(url, json=payload, headers=headers)
        print("MONITORING COLDSTART:", r.status_code, r.text)

    except Exception as e:
        print("Monitoring error:", e)


# --------------------------------------------------
# Automata Cold & Start
# --------------------------------------------------

def automata_coldstart():
    try:
        # Variables Vercel
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        root_id = os.environ.get("CENTRAL_ROOT_ID")

        if not service_json or not root_id:
            return {"status": "error", "message": "Missing environment variables"}

        # Auth Google
        service_info = json.loads(service_json)
        creds = service_account.Credentials.from_service_account_info(
            service_info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        # Année + mois
        year = "2025"
        months = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        # ----------------------------
        # 1) Dossiers fixes racine
        # ----------------------------
        clients_id = create_folder(drive, "Clients", root_id)
        factures_id = create_folder(drive, "Factures", root_id)
        archives_id = create_folder(drive, "Archives", root_id)
        monitoring_id = create_folder(drive, "Monitoring", root_id)
        templates_id = create_folder(drive, "Templates", root_id)

        # ----------------------------
        # 2) Templates (fixes)
        # ----------------------------
        create_folder(drive, "Factures", templates_id)
        create_folder(drive, "Devis", templates_id)
        create_folder(drive, "Contrats", templates_id)
        create_folder(drive, "Relances", templates_id)

        # ----------------------------
        # 3) Factures / 2025 / 12 mois
        # ----------------------------
        factures_year = create_folder(drive, year, factures_id)
        for m in months:
            create_folder(drive, m, factures_year)

        # ----------------------------
        # 4) Archives / 2025 / 12 mois
        # ----------------------------
        archives_year = create_folder(drive, year, archives_id)
        for m in months:
            create_folder(drive, m, archives_year)

        # ----------------------------
        # 5) Monitoring / Logs / 2025 / 12 mois
        # ----------------------------
        logs_root = create_folder(drive, "Logs", monitoring_id)
        logs_year = create_folder(drive, year, logs_root)
        for m in months:
            create_folder(drive, m, logs_year)

        # Monitoring succès
        send_monitoring(
            automata="ColdStart",
            client="SYSTEM",
            module="Python Engine - ColdStart",
            status="Succès",
            message="Cold & Start terminé"
        )

        # Retour des IDs fixes
        return {
            "status": "success",
            "clients_root_id_python": clients_id,
            "factures_root_id_python": factures_id,
            "archives_root_id_python": archives_id,
            "monitoring_logs_root_id_python": logs_root,
            "templates_root_id_python": templates_id
        }

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
