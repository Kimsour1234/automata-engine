def send_monitoring(automata, client, module, step, status, message, metadata):
    try:
        airtable_api = os.environ.get("AIRTABLE_API_KEY")
        base_id = os.environ.get("AIRTABLE_BASE_ID")
        table = os.environ.get("AIRTABLE_TABLE_NAME")

        url = f"https://api.airtable.com/v0/{base_id}/{table}"

        payload = {
            "fields": {
                "Monitoring": f"Log {datetime.datetime.utcnow().isoformat()}",
                "Automata": automata,             # ex: "AutoFacture"
                "Client": client,                 # ex: "CLI_024"
                "Type": "Log",                    # toujours
                "Statut": status,                 # success / error
                "Module": module,                 # ex: "AutoFacture"
                "Step": step,                     # ex: "gmail_send"
                "Message": message,               # court
                "Metadata": json.dumps(metadata), # optionnel mais utile
                "Date": datetime.datetime.utcnow().isoformat() + "Z"
            }
        }

        headers = {
            "Authorization": f"Bearer {airtable_api}",
            "Content-Type": "application/json"
        }

        requests.post(url, json=payload, headers=headers)

    except Exception as e:
        print("ERROR MONITORING:", str(e))
