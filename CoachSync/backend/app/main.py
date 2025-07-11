# Dummy FastAPI app for CoachSync backend
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "CoachSync backend API"}

@app.post("/upload-audio/")
async def upload_audio(file: UploadFile = File(...)):
    # Dummy: Save file, trigger transcription job
    return {"filename": file.filename, "status": "received"}

@app.get("/sessions/")
def get_sessions():
    # Dummy: Return list of sessions
    return [{"id": 1, "summary": "Session 1 summary"}]

@app.post("/transcribe/")
def transcribe():
    # Dummy: Trigger transcription
    return {"status": "transcription started"}

@app.post("/summarize/")
def summarize():
    # Dummy: Trigger summarization
    return {"status": "summarization started"}
