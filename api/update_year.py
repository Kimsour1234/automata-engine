from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# --------------------------------------------------
# Création de dossier
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

def send_monitoring(status, message):
    try:
        api = os.environ.get("AIRTABLE_API_KEY")
        base = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")

        url = f"https://api.airtable.com/v0/{base}/{table}"

        payload = {
            "fields": {
                "Monitoring": f"Log {datetime.datetime.utcnow().isoformat()}",
                "Automata": "AutoDossier",
                "Client": "-",
                "Type": "Log",
                "Statut": status,
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
# AUTOMATA – UPDATE YEAR (13 IDs)
# --------------------------------------------------

def automata_update_year(year_target,
                         factures_root_id,
                         archives_root_id,
                         monitoring_root_id,

                         client_folder_id_python,
                         factures_folder_id_python,
                         backups_factures_folder_id_python,
                         backups_relances_folder_id_python,
                         devis_folder_id_python,
                         contrats_folder_id_python,
                         docs_relances_folder_id_python,
                         R1_folder_id_python,
                         R2_folder_id_python,
                         R3_folder_id_python
                         ):

    try:
        # Auth Google
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        drive = build("drive", "v3", credentials=creds)

        # Mois FR
        mois_fr = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]

        # --------------------------------------------------
        # 1) Dossiers GÉNÉRAUX dynamiques
        # --------------------------------------------------

        year_factures_root = create_folder(drive, year_target, factures_root_id)
        for m in mois_fr:
            create_folder(drive, m, year_factures_root)

        year_archives_root = create_folder(drive, year_target, archives_root_id)
        for m in mois_fr:
            create_folder(drive, m, year_archives_root)

        year_monitoring_root = create_folder(drive, year_target, monitoring_root_id)
        for m in mois_fr:
            create_folder(drive, m, year_monitoring_root)


        # --------------------------------------------------
        # 2) Dossiers CLIENT dynamiques
        # --------------------------------------------------

        year_factures_client = create_folder(drive, year_target, factures_folder_id_python)
        for m in mois_fr:
            create_folder(drive, m, year_factures_client)

        year_backup_factures = create_folder(drive, year_target, backups_factures_folder_id_python)
        for m in mois_fr:
            create_folder(drive, m, year_backup_factures)

        year_backup_relances = create_folder(drive, year_target, backups_relances_folder_id_python)
        for m in mois_fr:
            create_folder(drive, m, year_backup_relances)

        year_devis = create_folder(drive, year_target, devis_folder_id_python)
        for m in mois_fr:
            create_folder(drive, m, year_devis)

        year_contrats = create_folder(drive, year_target, contrats_folder_id_python)
        for m in mois_fr:
            create_folder(drive, m, year_contrats)

        # ❗IMPORTANT : docs_relances, R1, R2, R3 = NE BOUGENT JAMAIS
        # Donc rien ici.


        # --------------------------------------------------
        # Monitoring OK
        # --------------------------------------------------

        send_monitoring(
            status="Succès",
            message=f"Nouvelle année {year_target} générée sur 13 dossiers"
        )

        return {"status": "success"}

    except Exception as e:

        send_monitoring(
            status="Erreur",
            message=str(e)
        )

        return {"status": "error", "message": str(e)}



# --------------------------------------------------
# Serveur Vercel
# --------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        length = int(self.headers.get("Content-Length"))
        body = self.rfile.read(length)
        data = json.loads(body.decode("utf-8"))

        if data.get("trigger") == "update_year":

            response = automata_update_year(
                year_target=data.get("year"),

                factures_root_id=data.get("factures_root_id"),
                archives_root_id=data.get("archives_root_id"),
                monitoring_root_id=data.get("monitoring_root_id"),

                client_folder_id_python=data.get("client_folder_id_python"),
                factures_folder_id_python=data.get("factures_folder_id_python"),
                backups_factures_folder_id_python=data.get("backups_factures_folder_id_python"),
                backups_relances_folder_id_python=data.get("backups_relances_folder_id_python"),
                devis_folder_id_python=data.get("devis_folder_id_python"),
                contrats_folder_id_python=data.get("contrats_folder_id_python"),
                docs_relances_folder_id_python=data.get("docs_relances_folder_id_python"),

                R1_folder_id_python=data.get("R1_folder_id_python"),
                R2_folder_id_python=data.get("R2_folder_id_python"),
                R3_folder_id_python=data.get("R3_folder_id_python")
            )

        else:
            response = {"error": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
