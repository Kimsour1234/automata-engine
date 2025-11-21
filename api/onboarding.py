from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def test():
    return {"status": "ok", "message": "Automata Engine Python API online"}

handler = app

