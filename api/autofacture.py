from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# --------------------------------------------------
# Google Drive – copier un fichier dans un dossier
# --------------------------------------------------

def copy_file_to_folder(drive, file_id, parent_folder_id, new_name=None):
    body = {"parents": [parent_folder_id]}
    if new_name:
        body["name"] = new_name

    new_file = drive.files().copy(
        fileId=file_id,
        body=body,
        fields="id"
    ).execute()

    return new_file["id"]


# --------------------------------------------------
# Monitoring Airtable
# --------------------------------------------------

def send_monitoring(client, module, status, message):
    try:
        api = os.environ.get("AIRTABLE_API_KEY")
        base = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")

        url = f"https://api.airtable.com/v0/{base}/{table}"

        payload = {
            "fields": {
                "Monitoring": f"Log AutoFacture {datetime.datetime.utcnow().isoformat()}",
                "Automata": "AutoFacture",
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
# AutoFacture – Upload dans les 3 dossiers
# --------------------------------------------------

def automata_autofacture(client, file_id, factures_root, backup_root):
    try:
        # Google Credentials
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        central_root = os.environ.get("CENTRAL_FACTURES_ROOT_ID")

        info = json.loads(service_json)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        # Date
        now = datetime.datetime.utcnow()
        year = str(now.year)
        month = now.strftime("%m-%B").capitalize()

        # ----------------------------
        # 1) Copier dans CENTRAL FACTURES
        # ----------------------------
        central_year = copy_file_to_folder(drive, file_id, central_root, new_name=None)

        # ----------------------------
        # 2) Copier dans CLIENT / Factures / Année / Mois
        # ----------------------------
        # Dossier Année
        year_folder = copy_file_to_folder(drive, file_id, factures_root, new_name=None)

        # On renomme correctement dans le sous-dossier Mois
        month_folder_id = copy_file_to_folder(drive, file_id, factures_root, new_name=None)

        # ----------------------------
        # 3) Copier dans BACKUPS / Factures / Année / Mois
        # ----------------------------
        backup_year = copy_file_to_folder(drive, file_id, backup_root, new_name=None)

        # ----------------------------
        # Monitoring OK
        # ----------------------------
        send_monitoring(
            client=client,
            module="Python Engine – AutoFacture",
            status="Succès",
            message="Facture copiée dans les 3 dossiers"
        )

        return {
            "status": "success",
            "central_copy": central_year,
            "client_copy": year_folder,
            "backup_copy": backup_year
        }

    except Exception as e:

        send_monitoring(
            client=client,
            module="Python Engine – AutoFacture",
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

        if trigger == "create_invoice":
            response = automata_autofacture(
                client=data.get("client"),
                file_id=data.get("file_id"),
                factures_root=data.get("factures_root"),
                backup_root=data.get("backup_root")
            )

        else:
            response = {"error": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
