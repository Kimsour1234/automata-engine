from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# --------------------------------------------------
# Create folder
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
# Monitoring
# --------------------------------------------------
def send_monitoring(client, module, status, message):
    try:
        api = os.environ.get("AIRTABLE_API_KEY")
        base = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")

        url = f"https://api.airtable.com/v0/{base}/{table}"

        payload = {
            "fields": {
                "Monitoring": f"Log UpdateYear {datetime.datetime.utcnow().isoformat()}",
                "Automata": "UpdateYear",
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
# AUTOMATA – Update Year (Central + Client)
# --------------------------------------------------
def automata_update_year(payload):

    try:
        # ---- ENV ----
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        # ---- INPUT ----
        client = payload.get("client")
        year_target = payload.get("year")

        # CENTRAL FIXES
        central_factures = payload.get("central_factures")
        central_archives = payload.get("central_archives")
        central_monitoring = payload.get("central_monitoring")

        # CLIENT FIXES
        factures_id = payload.get("factures_id")
        backup_factures_id = payload.get("backup_factures_id")
        backup_relances_id = payload.get("backup_relances_id")
        devis_id = payload.get("devis_id")
        contrats_id = payload.get("contrats_id")

        # ---- Mois ----
        mois_fr = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        # ----------------------------
        # CENTRAL ROOT → année + mois
        # ----------------------------
        central_year_factures = create_folder(drive, year_target, central_factures)
        central_year_archives = create_folder(drive, year_target, central_archives)
        central_year_monitoring = create_folder(drive, year_target, central_monitoring)

        for m in mois_fr:
            create_folder(drive, m, central_year_factures)
            create_folder(drive, m, central_year_archives)
            create_folder(drive, m, central_year_monitoring)

        # ----------------------------
        # CLIENT ROOT → année + mois
        # ----------------------------
        year_factures = create_folder(drive, year_target, factures_id)
        year_backup_factures = create_folder(drive, year_target, backup_factures_id)
        year_backup_relances = create_folder(drive, year_target, backup_relances_id)
        year_devis = create_folder(drive, year_target, devis_id)
        year_contrats = create_folder(drive, year_target, contrats_id)

        for m in mois_fr:
            create_folder(drive, m, year_factures)
            create_folder(drive, m, year_backup_factures)
            create_folder(drive, m, year_backup_relances)
            create_folder(drive, m, year_devis)
            create_folder(drive, m, year_contrats)

        # Monitoring OK
        send_monitoring(
            client=client,
            module="Python Engine – UpdateYear",
            status="Succès",
            message=f"Nouvelle année {year_target} générée (central + client)"
        )

        return {"status": "success"}

    except Exception as e:
        send_monitoring(
            client=client,
            module="Python Engine – UpdateYear",
            status="Erreur",
            message=str(e)
        )
        return {"status": "error", "message": str(e)}



# --------------------------------------------------
# HTTP SERVER
# --------------------------------------------------
class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        length = int(self.headers.get("Content-Length"))
        body = self.rfile.read(length)
        data = json.loads(body.decode("utf-8"))

        trigger = data.get("trigger")

        if trigger == "update_year":
            response = automata_update_year(data)
        else:
            response = {"error": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
