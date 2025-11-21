from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Réponse simple pour tester que Vercel marche
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        body = {
            "status": "ok",
            "message": "Automata Engine Python est en ligne"
        }
        self.wfile.write(json.dumps(body).encode("utf-8"))
