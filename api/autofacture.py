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


def ensure_folder(drive, name, parent_id):
    """Retourne l'id du dossier s'il existe, sinon le crée."""
    query = (
        f"name = '{name}' and "
        f"'{parent_id}' in parents and "
        "mimeType = 'application/vnd.google-apps.folder' and "
        "trashed = false"
    )

    results = drive.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    return create_folder(drive, name, parent_id)


# --------------------------------------------------
# Monitoring Airtable
# --------------------------------------------------

def send_monitoring(automata, client, module, status, message):
    try:
        airtable_api = os.environ.get("AIRTABLE_API_KEY")
        base_id = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")  # ex : "Monitoring"

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
# Automata Autofacture – trouver / créer le dossier année+mois
# --------------------------------------------------

def automata_create_invoice(data):
    """
    Rôle :
    - Prend la date d'émission + l'id du dossier FACTURES du client
    - Crée (si besoin) /Factures/ANNEE/MOIS
    - Retourne l'id du dossier MOIS pour ranger la facture PDF
    """

    try:
        # ---------- 1) Variables reçues ----------
        client_name = data.get("client_name")
        company_name = data.get("company_name")

        factures_root_id = data.get("factures_id")      # id du dossier "Factures" du client
        date_emission = data.get("date_emission")       # ex: "2025-11-22" (formatDate Airtable)

        if not factures_root_id or not date_emission:
            return {
                "status": "error",
                "message": "factures_id ou date_emission manquant"
            }

        # ---------- 2) Auth Google Drive ----------
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not service_json:
            return {"status": "error", "message": "Missing GOOGLE_SERVICE_ACCOUNT_JSON"}

        service_info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            service_info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        # ---------- 3) Extraire année + mois ----------
        # On suppose que Make envoie un format ISO propre "YYYY-MM-DD"
        try:
            dt = datetime.datetime.fromisoformat(date_emission)
        except Exception:
            # si besoin tu peux adapter le parsing
            return {"status": "error", "message": "Format date_emission invalide"}

        year_str = str(dt.year)
        mois_fr = [
            "01-Janvier", "02-Février", "03-Mars", "04-Avril",
            "05-Mai", "06-Juin", "07-Juillet", "08-Août",
            "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"
        ]
        month_name = mois_fr[dt.month - 1]

        # ---------- 4) Dossier ANNEE sous Factures ----------
        year_folder_id = ensure_folder(drive, year_str, factures_root_id)

        # ---------- 5) Dossier MOIS sous ANNEE ----------
        month_folder_id = ensure_folder(drive, month_name, year_folder_id)

        # ---------- 6) Monitoring OK ----------
        send_monitoring(
            automata="AutoFacture",
            client=f"{client_name} {company_name}",
            module="Python Engine - Create Invoice Folder",
            status="Succès",
            message=f"Dossier {year_str}/{month_name} prêt pour la facture"
        )

        # ---------- 7) Retour vers Make ----------
        return {
            "status": "success",
            "year": year_str,
            "month": month_name,
            "target_folder_id": month_folder_id
        }

    except Exception as e:
        send_monitoring(
            automata="AutoFacture",
            client=data.get("client_name", ""),
            module="Python Engine - Create Invoice Folder",
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
            response = automata_create_invoice(data)
        else:
            response = {"status": "error", "message": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
