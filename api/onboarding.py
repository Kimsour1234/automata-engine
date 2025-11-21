from http.server import BaseHTTPRequestHandler
import json
import os

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        body = {
            "status": "ok",
            "message": "Automata Engine Python est en ligne (GET)"
        }
        self.wfile.write(json.dumps(body).encode("utf-8"))


    def do_POST(self):
        # Lire le body JSON
        content_length = int(self.headers.get('Content-Length', 0))
        raw_body = self.rfile.read(content_length)
        data = json.loads(raw_body.decode('utf-8'))

        client_name = data.get("client_name", "inconnu")
        year = data.get("year", 2025)

        # Lire les variables d'environnement Vercel
        service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        clients_root_id = os.environ.get("CLIENTS_ROOT_ID")

        # Préparation (pas encore de connexion Drive)
        response = {
            "status": "ok",
            "client_name": client_name,
            "year": year,
            "ready_for_drive": True,
            "env_check": {
                "has_service_account": service_account_json is not None,
                "has_clients_root_id": clients_root_id is not None
            }
        }

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
