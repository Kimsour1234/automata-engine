from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# --------------------------------------------------
# Création dossier Google Drive
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
                "Monitoring": f"Log {datetime.datetime.utcnow().isoformat()}",
                "Automata": "UpdateYear",
                "Client": "",
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

    except:
        pass



# --------------------------------------------------
# Automata Year Update Engine
# --------------------------------------------------

def update_year_engine(ids, year):

    try:
        # Auth Google
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        service_info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            service_info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        drive = build("drive", "v3", credentials=creds)

        # Mois FR
        mois_fr = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        new_year = str(year)

        results = {}

        # --- Fonction interne : créer année + mois ---
        def create_year_if_missing(parent_id, label):
            response = drive.files().list(
                q=f"'{parent_id}' in parents and name = '{new_year}' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()

            if response.get("files"):
                # L'année existe déjà
                return response["files"][0]["id"]

            # L'année n'existe pas → on la crée
            year_id = create_folder(drive, new_year, parent_id)

            # créer 12 mois
            for m in mois_fr:
                create_folder(drive, m, year_id)

            return year_id


        # Créer année dans tous les dossiers parents
        results["factures_year_id"] = create_year_if_missing(ids["factures"], "Factures")
        results["backup_factures_year_id"] = create_year_if_missing(ids["backup_factures"], "Backup Factures")
        results["backup_relances_year_id"] = create_year_if_missing(ids["backup_relances"], "Backup Relances")
        results["devis_year_id"] = create_year_if_missing(ids["devis"], "Devis")
        results["contrats_year_id"] = create_year_if_missing(ids["contrats"], "Contrats")

        send_monitoring(
            "UpdateYear Engine",
            "Succès",
            f"Année {new_year} créée pour tous les dossiers parents"
        )

        return {"status": "success", "year": new_year, "ids": results}

    except Exception as e:

        send_monitoring(
            "UpdateYear Engine",
            "Erreur",
            str(e)
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

        # IDs envoyés depuis Make
        ids = {
            "factures": data.get("factures_id"),
            "backup_factures": data.get("backup_factures_id"),
            "backup_relances": data.get("backup_relances_id"),
            "devis": data.get("devis_id"),
            "contrats": data.get("contrats_id")
        }

        year = int(data.get("year"))

        response = update_year_engine(ids, year)

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
