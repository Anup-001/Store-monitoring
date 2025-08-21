from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Integer, DateTime, Time

Base = declarative_base()

class StoreStatus(Base):
    __tablename__ = "store_status"
    store_id = Column(String, primary_key=True)
    timestamp_utc = Column(DateTime, primary_key=True)
    status = Column(String)

class BusinessHour(Base):
    __tablename__ = "business_hours"
    store_id = Column(String, primary_key=True)
    day_of_week = Column(Integer, primary_key=True)
    start_time_local = Column(Time)
    end_time_local = Column(Time)

class Timezone(Base):
    __tablename__ = "timezones"
    store_id = Column(String, primary_key=True)
    timezone_str = Column(String)

class ReportStatus(Base):
    __tablename__ = "report_status"
    report_id = Column(String, primary_key=True)
    status = Column(String)
