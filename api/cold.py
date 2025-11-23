from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# ------------------------------------------------------------
# CREATE GOOGLE DRIVE FOLDER
# ------------------------------------------------------------
def create_folder(drive, name, parent_id):
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    folder = drive.files().create(body=metadata, fields="id").execute()
    return folder["id"]


# ------------------------------------------------------------
# MONITORING
# ------------------------------------------------------------
def send_monitoring(status, message):
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
                "Type": "Log",
                "Statut": status,
                "Module": "Python Engine – ColdStart",
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


# ------------------------------------------------------------
# COLD START – CREATE FULL CENTRAL STRUCTURE
# ------------------------------------------------------------
def cold_start():

    try:
        # --- 1) GOOGLE AUTH ---
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        root_id = os.environ.get("CENTRAL_ROOT_ID")

        info = json.loads(service_json)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)


        # --- 2) CREATE FIXED BRANCHES ---
        archives_id = create_folder(drive, "Archives", root_id)
        factures_id = create_folder(drive, "Factures", root_id)
        monitoring_id = create_folder(drive, "Monitoring", root_id)
        relances_id = create_folder(drive, "Relances", root_id)
        templates_id = create_folder(drive, "Templates", root_id)


        # --- 3) CREATE SUBFOLDERS ---
        logs_id = create_folder(drive, "Logs", monitoring_id)

        templates_factures = create_folder(drive, "Factures", templates_id)
        templates_devis = create_folder(drive, "Devis", templates_id)
        templates_contrats = create_folder(drive, "Contrats", templates_id)
        templates_relances = create_folder(drive, "Relances", templates_id)


        # --- 4) CREATE DYNAMIC YEAR + MONTHS ---
        now_year = str(datetime.datetime.utcnow().year)
        months = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        # Archives → année + mois
        year_archives = create_folder(drive, now_year, archives_id)
        for m in months:
            create_folder(drive, m, year_archives)

        # Factures → année + mois
        year_factures = create_folder(drive, now_year, factures_id)
        for m in months:
            create_folder(drive, m, year_factures)

        # Relances → année + mois
        year_relances = create_folder(drive, now_year, relances_id)
        for m in months:
            create_folder(drive, m, year_relances)


        # --- 5) MONITORING ---
        send_monitoring("Succès", "Cold Start exécuté avec succès")


        # --- 6) RETURN ALL IDS ---
        return {
            "status": "success",

            "archives_id": archives_id,
            "factures_id": factures_id,
            "monitoring_id": monitoring_id,
            "relances_id": relances_id,
            "templates_id": templates_id,

            "logs_id": logs_id,

            "templates_factures": templates_factures,
            "templates_devis": templates_devis,
            "templates_contrats": templates_contrats,
            "templates_relances": templates_relances,

            "year_archives": year_archives,
            "year_factures": year_factures,
            "year_relances": year_relances
        }

    except Exception as e:
        send_monitoring("Erreur", str(e))
        return {"error": str(e)}



# ------------------------------------------------------------
# HTTP SERVER
# ------------------------------------------------------------
class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        length = int(self.headers.get("Content-Length"))
        body = self.rfile.read(length)
        data = json.loads(body.decode("utf-8"))

        trigger = data.get("trigger")

        if trigger == "cold_start":
            response = cold_start()
        else:
            response = {"error": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
