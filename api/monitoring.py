import json
from datetime import datetime

def handler(request):
    try:
        body = request.json()

        module = body.get("module", "Unknown")
        step = body.get("step", "Unknown")
        status = body.get("status", "Undefined")
        message = body.get("message", "")
        client_id = body.get("client_id", "Unknown")
        metadata = body.get("metadata", {})

        timestamp = datetime.utcnow().isoformat()

        log_entry = {
            "module": module,
            "step": step,
            "status": status,
            "message": message,
            "client_id": client_id,
            "metadata": metadata,
            "timestamp": timestamp
        }

        return {
            "statusCode": 200,
            "body": json.dumps({"ok": True, "log": log_entry})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
