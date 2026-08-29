from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def initialyzation():
    return "Welcome to ProofPick"