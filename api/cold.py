# --------------------------------------------------
# PYTHON — VERSION PROVISOIRE
# Test lecture variable CENTRAL_DOGMA_ROOT_ID
# --------------------------------------------------

from http.server import BaseHTTPRequestHandler
import json, os

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        central_id = os.environ.get("CENTRAL_DOGMA_ROOT_ID")

        response = {
            "status": "ok",
            "central_dogma_root_id": central_id
        }

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
