import pandas as pd
from datetime import datetime
from app.models import StoreStatus, BusinessHour, Timezone
import logging

logger = logging.getLogger(__name__)

def load_from_external_db(db):
    try:
        store_status_chunks = pd.read_csv('data/store_status1.5.csv', chunksize=10000)
        business_hours_df = pd.read_csv('data/menu_hours.csv')
        timezones_df = pd.read_csv('data/timezones.csv')

        for chunk in store_status_chunks:
            for index, row in chunk.iterrows():
                db.merge(StoreStatus(
                    store_id=row['store_id'],
                    timestamp_utc=datetime.strptime(row['timestamp_utc'], "%Y-%m-%d %H:%M:%S.%f %Z"),
                    status=row['status']
                ))

        for index, row in business_hours_df.iterrows():
            db.merge(BusinessHour(
                store_id=row['store_id'],
                day_of_week=row['dayOfWeek'],
                start_time_local=datetime.strptime(row['start_time_local'], "%H:%M:%S").time(),
                end_time_local=datetime.strptime(row['end_time_local'], "%H:%M:%S").time()
            ))

        for index, row in timezones_df.iterrows():
            db.merge(Timezone(
                store_id=row['store_id'],
                timezone_str=row['timezone_str']
            ))

        db.commit()  
        logger.info("Data loading completed successfully.")
    except Exception as e:
        logger.error(f"Error loading data from external databases: {e}")
        raise e