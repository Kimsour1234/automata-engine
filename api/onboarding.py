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
        table = os.environ.get("AIRTABLE_TABLE_NAME")   # Doit être : Monitoring

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
        print("MONITORING:", r.status_code, r.text)

    except Exception as e:
        print("Monitoring error:", e)



# --------------------------------------------------
# Automata Onboarding
# --------------------------------------------------

def automata_onboarding(client_name, company_name, year):

    try:
        # Variables Vercel
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        clients_root = os.environ.get("CLIENTS_ROOT_ID")

        if not service_json or not clients_root:
            return {"error": "Missing environment variables"}

        # Auth Google
        service_info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            service_info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        drive = build("drive", "v3", credentials=creds)
        raise Exception("Test erreur volontaire")

        # Année + mois français
        now = datetime.datetime.utcnow()
        year_str = str(now.year)

        mois_fr = [
            "01-Janvier",
            "02-Février",
            "03-Mars",
            "04-Avril",
            "05-Mai",
            "06-Juin",
            "07-Juillet",
            "08-Août",
            "09-Septembre",
            "10-Octobre",
            "11-Novembre",
            "12-Décembre"
        ]

        # ----------------------------
        # 1) Dossier Client (nom complet ajouté ici)
        # ----------------------------
        folder_name = f"{client_name} {company_name}".strip()
        client_folder = create_folder(drive, folder_name, clients_root)

        # ----------------------------
        # 2) FACTURES / année / 12 mois
        # ----------------------------
        factures = create_folder(drive, "Factures", client_folder)
        factures_year = create_folder(drive, year_str, factures)
        for m in mois_fr:
            create_folder(drive, m, factures_year)

        # ----------------------------
        # 3) BACKUPS
        # ----------------------------
        backups = create_folder(drive, "Backups", client_folder)

        # Backups / Factures / année / 12 mois
        backup_factures = create_folder(drive, "Factures", backups)
        backup_factures_year = create_folder(drive, year_str, backup_factures)
        for m in mois_fr:
            create_folder(drive, m, backup_factures_year)

        # Backups / Relances / année / 12 mois
        backup_relances = create_folder(drive, "Relances", backups)
        backup_relances_year = create_folder(drive, year_str, backup_relances)
        for m in mois_fr:
            create_folder(drive, m, backup_relances_year)

        # ----------------------------
        # 4) DEVIS / année / 12 mois
        # ----------------------------
        devis = create_folder(drive, "Devis", client_folder)
        devis_year = create_folder(drive, year_str, devis)
        for m in mois_fr:
            create_folder(drive, m, devis_year)

        # ----------------------------
        # 5) DOCS → RELANCES (R1/R2/R3)
        # ----------------------------
        docs = create_folder(drive, "Docs", client_folder)
        docs_relances = create_folder(drive, "Relances", docs)

        for r in ["R1", "R2", "R3"]:
            create_folder(drive, r, docs_relances)

        # ----------------------------
        # 6) CONTRATS / année / 12 mois
        # ----------------------------
        contrats = create_folder(drive, "Contrats", client_folder)
        contrats_year = create_folder(drive, year_str, contrats)
        for m in mois_fr:
            create_folder(drive, m, contrats_year)

        # ----------------------------
        # Monitoring Succès
        # ----------------------------
        send_monitoring(
            automata="Onboarding",
            client=f"{client_name} {company_name}",
            module="Python Engine - Onboarding",
            status="Succès",
            message=f"Onboarding complet pour {client_name} {company_name}"
        )

        return {
            "status": "success",
            "client_folder": client_folder
        }

    except Exception as e:
        # Monitoring Erreur
        send_monitoring(
            automata="Onboarding",
            client=f"{client_name} {company_name}",
            module="Python Engine - Onboarding",
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

        client_name = data.get("client_name")          # Nom du client
        company_name = data.get("company_name")        # Nom de l'entreprise
        year = int(data.get("year", 2025))
        trigger = data.get("trigger", "create_folders")

        if trigger == "create_folders":
            response = automata_onboarding(client_name, company_name, year)
        else:
            response = {"error": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
