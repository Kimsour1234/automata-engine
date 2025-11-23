from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# --------------------------------------------------
# Google Drive – création dossier
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
                "Monitoring": f"Log ColdStart {datetime.datetime.utcnow().isoformat()}",
                "Automata": "ColdStart",
                "Client": "SYSTEM",
                "Type": "ColdStart",
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
# ColdStart — Création structure centrale
# --------------------------------------------------

def automata_coldstart():

    try:
        # Credentials Google
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        central_root = os.environ.get("CENTRAL_ROOT_ID")

        if not service_json or not central_root:
            return {"error": "Missing environment variables"}

        info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        drive = build("drive", "v3", credentials=creds)

        # --- Création des dossiers principaux ---
        factures_root = create_folder(drive, "Factures", central_root)
        archives_root = create_folder(drive, "Archives", central_root)
        templates_root = create_folder(drive, "Templates", central_root)

        # --- Sous-dossiers Templates ---
        create_folder(drive, "Factures", templates_root)
        create_folder(drive, "Devis", templates_root)
        create_folder(drive, "Contrats", templates_root)
        create_folder(drive, "Relances", templates_root)

        # --- Monitoring OK ---
        send_monitoring(
            module="ColdStart Engine",
            status="Succès",
            message="ColdStart terminé – structure centrale créée."
        )

        # --- Retour des 3 IDs fixes ---
        return {
            "status": "success",
            "factures_root_id": factures_root,
            "archives_root_id": archives_root,
            "templates_root_id": templates_root
        }

    except Exception as e:

        send_monitoring(
            module="ColdStart Engine",
            status="Erreur",
            message=str(e)
        )

        return {"status": "error", "message": str(e)}


# --------------------------------------------------
# Serveur HTTP Vercel
# --------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        response = automata_coldstart()

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
