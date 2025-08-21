import logging
from fastapi import FastAPI, BackgroundTasks
from app.database import engine, SessionLocal
from app.models import Base, ReportStatus
from app.utils import load_from_external_db
from app.report_manager import generate_report
import uuid
import os
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Starting up the application...")
        db = SessionLocal()
        
        logger.info("Loading data from external databases...")
        load_from_external_db(db)
        
        logger.info("External data loaded successfully.")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise e
    yield

app = FastAPI(lifespan=lifespan)

Base.metadata.create_all(bind=engine)

@app.post("/trigger_report")
def trigger_report(background_tasks: BackgroundTasks):
    report_id = str(uuid.uuid4()) 
    db = SessionLocal()
    db.add(ReportStatus(report_id=report_id, status="Running"))
    db.commit()
    
    background_tasks.add_task(generate_report, report_id)
    return {"report_id": report_id}

@app.get("/get_report")
def get_report(report_id: str):
    db = SessionLocal()
    report = db.query(ReportStatus).filter_by(report_id=report_id).first()
    if not report:
        return {"error": "Invalid report_id"}
    
    if report.status == "Running":
        return {"status": "Running"}
    
    file_path = os.path.join("reports", f"{report_id}.csv")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='text/csv', filename=f"{report_id}.csv")
    else:
        return {"error": "Report file missing"}
@app.get("/")
def read_root():
    return {"message": "Welcome to the Store Monitoring API!"}

@app.get("/favicon.ico")
async def favicon():
    return {"message": "No favicon set"}