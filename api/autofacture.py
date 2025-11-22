from http.server import BaseHTTPRequestHandler
import json, os, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests


# --------------------------------------------------
# Google Drive : copier un fichier (template → facture)
# --------------------------------------------------

def copy_file(drive, template_id, new_name, parent_id):
    file_metadata = {
        'name': new_name,
        'parents': [parent_id]
    }
    copied = drive.files().copy(
        fileId=template_id,
        body=file_metadata
    ).execute()
    return copied["id"]


# --------------------------------------------------
# Monitoring Airtable
# --------------------------------------------------

def send_monitoring(automata, client, module, status, message):
    try:
        api = os.environ.get("AIRTABLE_API_KEY")
        base = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")

        url = f"https://api.airtable.com/v0/{base}/{table}"

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
            "Authorization": f"Bearer {api}",
            "Content-Type": "application/json"
        }

        requests.post(url, json=payload, headers=headers)

    except:
        pass



# --------------------------------------------------
# Python Autofacture Engine
# --------------------------------------------------

def automata_autofacture(data):

    try:
        # Credentials Google
        service_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        template_id = os.environ.get("INVOICE_TEMPLATE_ID")

        service_info = json.loads(service_json)

        creds = service_account.Credentials.from_service_account_info(
            service_info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        # ------------------------------
        # RÉCUPÉRATION DES VALEURS JSON
        ------------------------------

        client = data.get("client")
        company = data.get("company")
        facture_numero = data.get("ID_FACTURE")

        # Emplacements Drive
        factures_root = data.get("factures_id")
        backup_factures_root = data.get("backup_factures_id")

        # Champs facture
        date_emission = data.get("DATE_EMISSION")
        date_limite = data.get("DATE_LIMITE")
        mode_paiement = data.get("MODE_PAIEMENT")

        total_ht = data.get("TOTAL_HT")
        tva_percent = data.get("TVA_POURCENT")
        montant_tva = data.get("MONTANT_TVA")
        total_ttc = data.get("TOTAL_TTC")

        # LIGNE 1
        p1 = data.get("Prestation 1")
        q1 = data.get("Quantité 1")
        pu1 = data.get("PU HT 1(€)")
        t1 = data.get("Total HT 1 (€)")

        # LIGNE 2
        p2 = data.get("Prestation 2")
        q2 = data.get("Quantité 2")
        pu2 = data.get("PU HT 2(€)")
        t2 = data.get("Total HT 2 (€)")

        # Format PRO
        ligne1 = f"• {p1} ({q1} × {pu1} € HT) = {t1} €" if p1 else ""
        ligne2 = f"• {p2} ({q2} × {pu2} € HT) = {t2} €" if p2 else ""

        # ------------------------------
        # Création dossier année/mois
        # ------------------------------

        now = datetime.datetime.utcnow()
        year = now.year
        month = now.month

        mois_fr = [
            "01-Janvier","02-Février","03-Mars","04-Avril","05-Mai","06-Juin",
            "07-Juillet","08-Août","09-Septembre","10-Octobre","11-Novembre","12-Décembre"
        ]

        month_name = mois_fr[month-1]

        # Créer dossier année si besoin
        year_folder = drive.files().create(
            body={
                "name": str(year),
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [factures_root]
            },
            fields="id"
        ).execute()["id"]

        # Créer dossier mois
        month_folder = drive.files().create(
            body={
                "name": month_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [year_folder]
            },
            fields="id"
        ).execute()["id"]

        # ------------------------------
        # Copier le template
        # ------------------------------

        pdf_name = f"Facture {facture_numero}.pdf"
        doc_name = f"Facture {facture_numero}"

        doc_id = copy_file(drive, template_id, doc_name, month_folder)

        # ------------------------------
        # Replace text
        # ------------------------------

        requests_post = drive.documents().batchUpdate(
            documentId=doc_id,
            body={
                "requests": [
                    {"replaceAllText": {"containsText": {"text": "{{CLIENT}}"}, "replaceText": client}},
                    {"replaceAllText": {"containsText": {"text": "{{ID_FACTURE}}"}, "replaceText": facture_numero}},
                    {"replaceAllText": {"containsText": {"text": "{{DATE_EMISSION}}"}, "replaceText": date_emission}},
                    {"replaceAllText": {"containsText": {"text": "{{DATE_LIMITE}}"}, "replaceText": date_limite}},
                    {"replaceAllText": {"containsText": {"text": "{{MODE_PAIEMENT}}"}, "replaceText": mode_paiement}},
                    {"replaceAllText": {"containsText": {"text": "{{LIGNE_1}}"}, "replaceText": ligne1}},
                    {"replaceAllText": {"containsText": {"text": "{{LIGNE_2}}"}, "replaceText": ligne2}},
                    {"replaceAllText": {"containsText": {"text": "{{TOTAL_HT}}"}, "replaceText": str(total_ht)}},
                    {"replaceAllText": {"containsText": {"text": "{{TVA_POURCENT}}"}, "replaceText": str(tva_percent)}},
                    {"replaceAllText": {"containsText": {"text": "{{MONTANT_TVA}}"}, "replaceText": str(montant_tva)}},
                    {"replaceAllText": {"containsText": {"text": "{{TOTAL_TTC}}"}, "replaceText": str(total_ttc)}},
                ]
            }
        ).execute()

        # ------------------------------
        # Export PDF
        # ------------------------------

        pdf_file = drive.files().export(
            fileId=doc_id,
            mimeType="application/pdf"
        ).execute()

        # Upload PDF final dans Drive
        uploaded_pdf = drive.files().create(
            body={
                "name": pdf_name,
                "parents": [month_folder],
                "mimeType": "application/pdf"
            },
            media_body=pdf_file,
            fields="id, webViewLink"
        ).execute()

        pdf_id = uploaded_pdf["id"]
        pdf_link = uploaded_pdf["webViewLink"]

        # Monitoring OK
        send_monitoring(
            automata="Autofacture",
            client=f"{client} {company}",
            module="Python Engine - Autofacture",
            status="Succès",
            message=f"Facture {facture_numero} générée"
        )

        return {
            "status": "success",
            "pdf_link": pdf_link,
            "pdf_id": pdf_id
        }


    except Exception as e:

        send_monitoring(
            automata="Autofacture",
            client=data.get("client"),
            module="Python Engine - Autofacture",
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

        if trigger == "autofacture":
            response = automata_autofacture(data)

        else:
            response = {"error": "Unknown trigger"}

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
