from http.server import BaseHTTPRequestHandler
import json, os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ------------------------------
# Fonction création de dossier
# ------------------------------
def create_folder(drive, name, parent_id):
    body = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    f = drive.files().create(body=body, fields="id").execute()
    return f["id"]

# ------------------------------
# TEST TOTAL 2026
# ------------------------------
def test_total_2026(data):

    # lecture variables
    service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not service_json:
        return {"error": " Missing GOOGLE_SERVICE_ACCOUNT_JSON "}

    service_info = json.loads(service_json)
    creds = service_account.Credentials.from_service_account_info(
        service_info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    drive = build("drive", "v3", credentials=creds)

    # mois FR
    mois = [
        "01-Janvier","02-Février","03-Mars","04-Avril","05-Mai","06-Juin",
        "07-Juillet","08-Août","09-Septembre","10-Octobre","11-Novembre","12-Décembre"
    ]

    year = "2026"

    # récupération des IDs envoyés par Make
    central_factures = data.get("central_factures_id")
    central_archives = data.get("central_archives_id")
    central_monitoring = data.get("central_monitoring_logs_id")

    client_factures = data.get("factures_id")
    client_backup_factures = data.get("backup_factures_id")
    client_backup_relances = data.get("backup_relances_id")
    client_devis = data.get("devis_id")
    client_contrats = data.get("contrats_id")
    client_docs_relances = data.get("docs_relances_id")

    # -------------------------
    # CREATION DES DOSSIERS 2026
    # -------------------------

    # CENTRAL ROOT
    c_fact_2026 = create_folder(drive, year, central_factures)
    c_arch_2026 = create_folder(drive, year, central_archives)
    c_mon_2026 = create_folder(drive, year, central_monitoring)

    # CLIENT
    cl_fact_2026 = create_folder(drive, year, client_factures)
    cl_bf_2026 = create_folder(drive, year, client_backup_factures)
    cl_br_2026 = create_folder(drive, year, client_backup_relances)
    cl_dev_2026 = create_folder(drive, year, client_devis)
    cl_con_2026 = create_folder(drive, year, client_contrats)

    # relances client → pas de dossier année, on ne crée rien


    # -------------------------
    # CREATION DES 12 MOIS
    # -------------------------

    def create_months(parent_id):
        out = {}
        for m in mois:
            mid = create_folder(drive, m, parent_id)
            out[m] = mid
        return out

    months = {
        "central_factures_months": create_months(c_fact_2026),
        "central_archives_months": create_months(c_arch_2026),
        "central_monitoring_months": create_months(c_mon_2026),

        "client_factures_months": create_months(cl_fact_2026),
        "client_backup_factures_months": create_months(cl_bf_2026),
        "client_backup_relances_months": create_months(cl_br_2026),
        "client_devis_months": create_months(cl_dev_2026),
        "client_contrats_months": create_months(cl_con_2026),
    }

    return {
        "status": "success",
        "year": year,

        "central_factures_2026": c_fact_2026,
        "central_archives_2026": c_arch_2026,
        "central_monitoring_2026": c_mon_2026,

        "client_factures_2026": cl_fact_2026,
        "client_backup_factures_2026": cl_bf_2026,
        "client_backup_relances_2026": cl_br_2026,
        "client_devis_2026": cl_dev_2026,
        "client_contrats_2026": cl_con_2026,

        "months": months
    }


# ------------------------------
# SERVEUR VERCEL
# ------------------------------
class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        length = int(self.headers.get("Content-Length"))
        raw = self.rfile.read(length)
        data = json.loads(raw.decode("utf-8"))

        response = test_total_2026(data)

        self.send_response(200)
        self.send_header("Content-type","application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
