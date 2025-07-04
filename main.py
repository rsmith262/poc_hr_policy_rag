#FastAPI wrapper

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from RAG_question_answer import handle_query # gets my query from RAG_question_answer.py
import os

from pydantic import BaseModel

app = FastAPI()

# CORS Configuration Toggle
# Cross-Origin Resource Sharing. This is important if you plan to call your API from a web browser or external app that is hosted on a different domain
# uses .env file to toggle on and off. If true it aloows all
# in production this should be toggled offa and only allow frontends we want it to be access from 
CORS_ALLOW_ALL = os.getenv("CORS_ALLOW_ALL", "true").lower() == "true"

if CORS_ALLOW_ALL:
    allowed_origins = ["*"]
else:
    # adjust this to match your actual frontends
    allowed_origins = [
        "https://teams.microsoft.com",
        "https://yourcompany.sharepoint.com",
        "https://yourcopilotapp.azurewebsites.net"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key check
# This checks fastapi api key - i set this and it's in .env file.
# this needs to be set in azure app services too Settings → Configuration → Application Settings:
API_KEY = os.getenv("API_KEY")

class QueryPayload(BaseModel):
    question: str


@app.post("/query")
async def query(payload: QueryPayload, request: Request):
    if API_KEY:
        client_key = request.headers.get("x-api-key")
        if client_key != API_KEY:
            raise HTTPException(status_code=403, detail="Unauthorized")

    question = payload.question
    if not question:
        raise HTTPException(status_code=400, detail="Missing 'question'")

    response = handle_query(question) # uses my query from RAG_question_answer.py
    return {"answer": response}