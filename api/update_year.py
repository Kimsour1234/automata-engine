from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# --------------------------------------------------
# Google Drive : création d’un dossier
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
# Monitoring Airtable
# --------------------------------------------------

def send_monitoring(automata, client, module, status, message):
    try:
        airtable_api = os.environ.get("AIRTABLE_API_KEY")
        base_id = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")  # Monitoring

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

        requests.post(url, json=payload, headers=headers)

    except Exception as e:
        print("Monitoring error:", e)



# --------------------------------------------------
# Automata – UpdateYear (Autodossier)
# --------------------------------------------------

def automata_update_year(client,
                         year_target,
                         central_factures_id,
                         central_archives_id,
                         monitoring_logs_id,
                         factures_id,
                         backup_factures_id,
                         devis_id,
                         contrats_id):

    try:
        # AUTH GOOGLE
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        # Mois français
        mois_fr = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        # --------------------------------------------------
        # 1) CENTRAL ROOT – Factures
        # --------------------------------------------------
        year_central_factures = create_folder(drive, year_target, central_factures_id)
        for m in mois_fr:
            create_folder(drive, m, year_central_factures)

        # --------------------------------------------------
        # 2) CENTRAL ROOT – Archives
        # --------------------------------------------------
        year_central_archives = create_folder(drive, year_target, central_archives_id)
        for m in mois_fr:
            create_folder(drive, m, year_central_archives)

        # --------------------------------------------------
        # 3) CENTRAL ROOT – Monitoring / Logs
        # --------------------------------------------------
        year_monitoring = create_folder(drive, year_target, monitoring_logs_id)
        for m in mois_fr:
            create_folder(drive, m, year_monitoring)

        # --------------------------------------------------
        # 4) CLIENT – Factures
        # --------------------------------------------------
        year_factures = create_folder(drive, year_target, factures_id)
        for m in mois_fr:
            create_folder(drive, m, year_factures)

        # --------------------------------------------------
        # 5) CLIENT – Backups / Factures
        # --------------------------------------------------
        year_backup_factures = create_folder(drive, year_target, backup_factures_id)
        for m in mois_fr:
            create_folder(drive, m, year_backup_factures)

        # --------------------------------------------------
        # 6) CLIENT – Devis
        # --------------------------------------------------
        year_devis = create_folder(drive, year_target, devis_id)
        for m in mois_fr:
            create_folder(drive, m, year_devis)

        # --------------------------------------------------
        # 7) CLIENT – Contrats
        # --------------------------------------------------
        year_contrats = create_folder(drive, year_target, contrats_id)
        for m in mois_fr:
            create_folder(drive, m, year_contrats)

        # --------------------------------------------------
        # ⚠️ AUCUNE ACTION SUR DOCS/RELANCES
        # --------------------------------------------------

        send_monitoring(
            automata="UpdateYear",
            client=client,
            module="AutoDossier – UpdateYear",
            status="Succès",
            message=f"Dossiers  {year_target} créés"
        )

        return {"status": "success"}

    except Exception as e:

        send_monitoring(
            automata="UpdateYear",
            client=client,
            module="AutoDossier – UpdateYear",
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

        if trigger == "update_year":

            response = automata_update_year(
                client=data.get("client"),
                year_target=data.get("year"),

                central_factures_id=data.get("central_factures_id"),
                central_archives_id=data.get("central_archives_id"),
                monitoring_logs_id=data.get("monitoring_logs_id"),

                factures_id=data.get("factures_id"),
                backup_factures_id=data.get("backup_factures_id"),
                devis_id=data.get("devis_id"),
                contrats_id=data.get("contrats_id")
            )

        else:
            response = {"error": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
