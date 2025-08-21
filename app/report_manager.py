from app.models import ReportStatus
from app.database import SessionLocal
import pandas as pd

def generate_report(report_id: str):
    db = SessionLocal()

    dummy = pd.DataFrame([{
        "store_id": "test",
        "uptime_last_hour": 60,
        "uptime_last_day": 24,
        "update_last_week": 160,
        "downtime_last_hour": 0,
        "downtime_last_day": 0,
        "downtime_last_week": 8
    }])
    
    dummy.to_csv(f"reports/{report_id}.csv", index=False)

    report = db.query(ReportStatus).filter_by(report_id=report_id).first()
    report.status = "Complete"
    db.commit()
