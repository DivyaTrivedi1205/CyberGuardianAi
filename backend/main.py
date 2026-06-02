from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "CyberGuardian AI Backend Running"}
