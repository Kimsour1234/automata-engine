import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler

# ------------------------------
# VARIABLES ENVIRONNEMENT VERCEL
# ------------------------------
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.environ.get("AIRTABLE_TABLE_NAME")  # "Monitoring"


class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        # --- Lire le JSON reçu ---
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length)

        try:
            data = json.loads(raw_body)
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"Invalid JSON: {e}".encode())
            return

        # Debug JSON reçu
        print("DEBUG - JSON reçu:", data)

        # -------------------------
        # Construire la requête Airtable
        # -------------------------
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"

        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }

        # Champs EXACTS Airtable
        airtable_fields = {
            "Workflow": data.get("Workflow", ""),
            "Module": data.get("Module", ""),
            "Sensor": data.get("Sensor", ""),      # log / error
            "Statut": data.get("Statut", ""),
            "Message": data.get("Message", ""),
            "Date": data.get("Date", "")
        }

        payload = json.dumps({"fields": airtable_fields}).encode()

        print("DEBUG - URL:", url)
        print("DEBUG - Data envoyée:", airtable_fields)

        # -------------------------
        # Envoi POST vers Airtable
        # -------------------------
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req) as response:
                resp_body = response.read()
                print("DEBUG - Airtable response:", resp_body)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
        except Exception as e:
            print("DEBUG - Airtable ERROR:", e)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Airtable error: {e}".encode())
