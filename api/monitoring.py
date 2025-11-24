import os
import json
import requests
from http.server import BaseHTTPRequestHandler

AIRTABLE_API_KEY = os.environ["AIRTABLE_API_KEY"]
AIRTABLE_BASE_ID = os.environ["AIRTABLE_BASE_ID"]
AIRTABLE_TABLE_ID = os.environ["AIRTABLE_TABLE_ID"]

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data)
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"Invalid JSON: {e}".encode())
            return

        # Préparation du record Airtable
        airtable_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_ID}"

        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "fields": {
                "module": payload.get("module", ""),
                "step": payload.get("step", ""),
                "status": payload.get("status", ""),
                "message": payload.get("message", ""),
                "client_id": payload.get("client_id", ""),
                "metadata": json.dumps(payload.get("metadata", {}))
            }
        }

        try:
            r = requests.post(airtable_url, headers=headers, json=data)

            if r.status_code == 200 or r.status_code == 201:
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
