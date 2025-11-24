import os
import json
import requests
from http.server import BaseHTTPRequestHandler

# ----------------------------
# VARIABLES ENV (Vercel)
# ----------------------------
AIRTABLE_API_KEY = os.environ["AIRTABLE_API_KEY"]
AIRTABLE_BASE_ID = os.environ["AIRTABLE_BASE_ID"]

TABLE_NAME = "Monitoring"  # Nom exact de la table Airtable


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        # Lire le JSON envoyé par Make
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data)
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"Invalid JSON: {e}".encode())
            return

        # ----------------------------
        # Construction requête Airtable
        # ----------------------------
        airtable_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{TABLE_NAME}"

        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }

        # Champs simples
        data = {
            "fields": {
                "module": payload.get("module", ""),
                "step": payload.get("step", ""),
                "status": payload.get("status", ""),
                "message": payload.get("message", "")
            }
        }

        # ----------------------------
        # Envoi vers Airtable
        # ----------------------------
        try:
            r = requests.post(airtable_url, headers=headers, json=data)

            if r.status_code in (200, 201):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Airtable error: {r.text}".encode())

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Request failed: {e}".encode())
