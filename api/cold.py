from http.server import BaseHTTPRequestHandler
import json, os
from google.oauth2 import service_account
from googleapiclient.discovery import build


# --------------------------------------------------
# Google Drive : création de dossier
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
# Cold & Dark : création du Central Dogma
# --------------------------------------------------

def cold_and_dark():

    # 1) récupérer la variable ENV Vercel (corrigé)
    root_id = os.environ.get("CENTRAL_ROOT_ID")

    if not root_id:
        return {"error": "Missing CENTRAL_ROOT_ID"}

    # 2) authentification Google
    service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    service_info = json.loads(service_json)

    creds = service_account.Credentials.from_service_account_info(
        service_info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    drive = build("drive", "v3", credentials=creds)

    # 3) création des dossiers fixes
    archives = create_folder(drive, "Archives", root_id)
    factures = create_folder(drive, "Factures", root_id)
    clients = create_folder(drive, "Clients", root_id)
    monitoring = create_folder(drive, "Monitoring", root_id)
    templates = create_folder(drive, "Templates", root_id)

    # 4) retour complet
    return {
        "status": "success",
        "root": root_id,
        "archives_id": archives,
        "factures_id": factures,
        "clients_id": clients,
        "monitoring_id": monitoring,
        "templates_id": templates
    }


# --------------------------------------------------
# Serveur HTTP (Vercel)
# --------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        length = int(self.headers.get("Content-Length"))
        body = self.rfile.read(length)
        data = json.loads(body.decode("utf-8"))

        trigger = data.get("trigger", "")

        if trigger == "cold_and_dark":
            response = cold_and_dark()
        else:
            response = {"error": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
