from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ---------------------------------------------
# Créer un sous-dossier dans un dossier
# ---------------------------------------------
def create_folder(drive, name, parent):
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent]
    }
    folder = drive.files().create(body=metadata, fields="id").execute()
    return folder["id"]

# ---------------------------------------------
# Créer l'arborescence dynamique année + mois
# ---------------------------------------------
def create_year_and_months(drive, root_id, year):
    year_id = create_folder(drive, year, root_id)

    months = [
        "01-Janvier", "02-Février", "03-Mars", "04-Avril",
        "05-Mai", "06-Juin", "07-Juillet", "08-Août",
        "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
    ]

    for m in months:
        create_folder(drive, m, year_id)

    return year_id

# ---------------------------------------------
# Moteur COLD & START
# ---------------------------------------------
def cold_and_start():
    # Lecture variables Vercel
    service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    central_root = os.environ.get("CENTRAL_ROOT_ID")
    base_id = os.environ.get("AIRTABLE_BASE_ID")
    api_key = os.environ.get("AIRTABLE_API_KEY")
    table_name = os.environ.get("AIRTABLE_COLD_TABLE", "Cold")

    if not central_root:
        return {"status": "error", "message": "CENTRAL_ROOT_ID manquant"}

    # Auth Google
    info = json.loads(service_json)
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    drive = build("drive", "v3", credentials=creds)

    # Récupération de l'unique ligne Airtable
    import requests
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    headers = {"Authorization": f"Bearer {api_key}"}
    r = requests.get(url, headers=headers).json()

    record_id = r["records"][0]["id"]
    fields = r["records"][0]["fields"]

    factures_root = fields.get("factures_root_id")
    archives_root = fields.get("archives_root_id")
    monitoring_root = fields.get("monitoring_root_id")

    # On crée les dossiers si absents
    if not factures_root:
        new_id = create_folder(drive, "Factures", central_root)
        fields["factures_root_id"] = new_id

    if not archives_root:
        new_id = create_folder(drive, "Archives", central_root)
        fields["archives_root_id"] = new_id

    if not monitoring_root:
        new_id = create_folder(drive, "Monitoring", central_root)
        logs_id = create_folder(drive, "Logs", new_id)
        fields["monitoring_root_id"] = logs_id

    # On met à jour Airtable
    payload = {"fields": fields}
    requests.patch(url + "/" + record_id, json=payload, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    })

    # Création dynamique année + mois
    year = str(datetime.datetime.utcnow().year)
    create_year_and_months(drive, fields["factures_root_id"], year)
    create_year_and_months(drive, fields["archives_root_id"], year)
    create_year_and_months(drive, fields["monitoring_root_id"], year)

    return {"status": "success", "message": "Cold & Start OK"}

# ---------------------------------------------
# Serveur HTTP (Vercel)
# ---------------------------------------------
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        response = cold_and_start()

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
