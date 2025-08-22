from datetime import datetime, timedelta, time, UTC
from typing import Dict, Iterable, List, Tuple
import os

import pandas as pd
import pytz
from sqlalchemy import func

from app.models import BusinessHour, ReportStatus, StoreStatus, Timezone
from app.database import SessionLocal


def generate_report(report_id: str):
    db = SessionLocal()
    try:
        current_time_utc = _get_current_time_utc(db)

        window_last_hour = (current_time_utc - timedelta(hours=1), current_time_utc)
        window_last_day = (current_time_utc - timedelta(days=1), current_time_utc)
        window_last_week = (current_time_utc - timedelta(days=7), current_time_utc)

        store_id_to_statuses = _fetch_all_statuses(db)
        store_id_to_timezone = _fetch_all_timezones(db)
        store_id_to_hours = _fetch_all_business_hours(db)

        results: List[Dict[str, object]] = []
        for store_id, status_events in store_id_to_statuses.items():
            timezone_str = store_id_to_timezone.get(store_id, "America/Chicago")
            tz = pytz.timezone(timezone_str)

            # Build business-hour intervals in UTC for each window
            bh_last_hour = _business_intervals_utc(store_id, tz, store_id_to_hours, *window_last_hour)
            bh_last_day = _business_intervals_utc(store_id, tz, store_id_to_hours, *window_last_day)
            bh_last_week = _business_intervals_utc(store_id, tz, store_id_to_hours, *window_last_week)

            uptime_min_h, downtime_min_h = _accumulate_minutes(status_events, window_last_hour, bh_last_hour)
            uptime_min_d, downtime_min_d = _accumulate_minutes(status_events, window_last_day, bh_last_day)
            uptime_min_w, downtime_min_w = _accumulate_minutes(status_events, window_last_week, bh_last_week)

            result_row: Dict[str, object] = {
                "store_id": store_id,
                "uptime_last_hour": int(round(uptime_min_h)),
                "uptime_last_day": round(uptime_min_d / 60.0, 2),
                "uptime_last_week": round(uptime_min_w / 60.0, 2),
                "downtime_last_hour": int(round(downtime_min_h)),
                "downtime_last_day": round(downtime_min_d / 60.0, 2),
                "downtime_last_week": round(downtime_min_w / 60.0, 2),
            }
            results.append(result_row)

        # Ensure reports directory exists
        os.makedirs("reports", exist_ok=True)
        pd.DataFrame(results).to_csv(f"reports/{report_id}.csv", index=False)

        report = db.query(ReportStatus).filter_by(report_id=report_id).first()
        if report is not None:
            report.status = "Complete"
            db.commit()
    except Exception:
        # On any failure, mark report as running to allow retry
        report = db.query(ReportStatus).filter_by(report_id=report_id).first()
        if report is not None:
            report.status = "Running"
            db.commit()


def _get_current_time_utc(db: SessionLocal) -> datetime:
    max_ts: datetime = db.query(func.max(StoreStatus.timestamp_utc)).scalar()  # type: ignore
    if max_ts is None:
        # Fallback to now if no data
        return datetime.now(UTC)
    return max_ts


def _fetch_all_statuses(db: SessionLocal) -> Dict[str, List[Tuple[datetime, str]]]:
    rows: List[StoreStatus] = db.query(StoreStatus).order_by(StoreStatus.store_id, StoreStatus.timestamp_utc).all()
    store_to_events: Dict[str, List[Tuple[datetime, str]]] = {}
    for row in rows:
        store_to_events.setdefault(row.store_id, []).append((row.timestamp_utc, row.status))
    return store_to_events


def _fetch_all_timezones(db: SessionLocal) -> Dict[str, str]:
    rows: List[Timezone] = db.query(Timezone).all()
    return {row.store_id: row.timezone_str for row in rows}


def _fetch_all_business_hours(db: SessionLocal) -> Dict[str, Dict[int, Tuple[time, time]]]:
    rows: List[BusinessHour] = db.query(BusinessHour).all()
    mapping: Dict[str, Dict[int, Tuple[time, time]]] = {}
    for row in rows:
        mapping.setdefault(row.store_id, {})[row.day_of_week] = (row.start_time_local, row.end_time_local)
    return mapping


def _business_intervals_utc(
    store_id: str,
    tz: pytz.BaseTzInfo,
    store_id_to_hours: Dict[str, Dict[int, Tuple[time, time]]],
    window_start_utc: datetime,
    window_end_utc: datetime,
) -> List[Tuple[datetime, datetime]]:
    if window_start_utc >= window_end_utc:
        return []

    hours_for_store = store_id_to_hours.get(store_id)

    # 24x7 if no hours defined
    if not hours_for_store:
        return [(window_start_utc, window_end_utc)]

    intervals: List[Tuple[datetime, datetime]] = []

    # Convert UTC window into local dates to iterate
    start_local = pytz.UTC.localize(window_start_utc).astimezone(tz)
    end_local = pytz.UTC.localize(window_end_utc).astimezone(tz)

    current_local_date = start_local.date()
    end_local_date = end_local.date()

    while current_local_date <= end_local_date:
        dow = (current_local_date.weekday())  # Monday=0
        if dow in hours_for_store:
            start_t, end_t = hours_for_store[dow]

            # Build local datetime ranges; handle overnight windows if end < start
            local_start_dt = tz.localize(datetime.combine(current_local_date, start_t))
            local_end_dt = tz.localize(datetime.combine(current_local_date, end_t))

            if end_t <= start_t:
                # Overnight: split into [start, midnight) and [midnight, end next day)
                midnight = tz.localize(datetime.combine(current_local_date, time(23, 59, 59)))
                next_day = current_local_date + timedelta(days=1)
                start_next = tz.localize(datetime.combine(next_day, time(0, 0, 0)))
                end_next = tz.localize(datetime.combine(next_day, end_t))
                local_ranges = [(local_start_dt, midnight), (start_next, end_next)]
            else:
                local_ranges = [(local_start_dt, local_end_dt)]

            for ls, le in local_ranges:
                # Clamp to window in local timezone
                clamped_start_local = max(ls, start_local)
                clamped_end_local = min(le, end_local)
                if clamped_start_local < clamped_end_local:
                    # Convert to UTC naive
                    s_utc = clamped_start_local.astimezone(pytz.UTC).replace(tzinfo=None)
                    e_utc = clamped_end_local.astimezone(pytz.UTC).replace(tzinfo=None)
                    # Clamp to original UTC bounds to avoid conversion edge shifts
                    s_utc = max(s_utc, window_start_utc)
                    e_utc = min(e_utc, window_end_utc)
                    if s_utc < e_utc:
                        intervals.append((s_utc, e_utc))

        current_local_date += timedelta(days=1)

    return intervals


def _accumulate_minutes(
    status_events: List[Tuple[datetime, str]],
    window: Tuple[datetime, datetime],
    business_intervals: List[Tuple[datetime, datetime]],
    ) -> Tuple[float, float]:
    if not business_intervals:
        return 0.0, 0.0

    window_start, window_end = window

    # Prepare change points within the window expanded by one event before start and after end
    # Find index of first event after start
    times = [ts for ts, _ in status_events]
    idx = 0
    while idx < len(times) and times[idx] <= window_start:
        idx += 1

    # Determine status at window_start (carry last known or default inactive)
    current_status = "inactive"
    if idx > 0:
        current_status = status_events[idx - 1][1]

    # Build list of change points within (window_start, window_end]
    change_points: List[Tuple[datetime, str]] = []
    j = idx
    while j < len(status_events) and status_events[j][0] <= window_end:
        change_points.append(status_events[j])
        j += 1

    uptime_minutes = 0.0
    downtime_minutes = 0.0

    # Iterate over business intervals and integrate status over them
    for b_start, b_end in business_intervals:
        t = max(b_start, window_start)
        # Process changes within this business interval
        for cp_time, cp_status in change_points:
            if cp_time <= t:
                current_status = cp_status
                continue
            if cp_time > b_end:
                break
            segment_end = min(cp_time, b_end)
            delta_min = (segment_end - t).total_seconds() / 60.0
            if delta_min > 0:
                if current_status == "active":
                    uptime_minutes += delta_min
                else:
                    downtime_minutes += delta_min
            t = cp_time
            current_status = cp_status

        # Tail segment to end of business interval
        if t < b_end:
            delta_min = (b_end - t).total_seconds() / 60.0
            if current_status == "active":
                uptime_minutes += delta_min
            else:
                downtime_minutes += delta_min

    return uptime_minutes, downtime_minutes
