"""Periodic appointment cleanup with a patient-safe notification boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from infrai_client import InfraiClient


@dataclass(frozen=True)
class Appointment:
    appointment_id: str
    patient_ref: str
    status: str
    updated_at: datetime


def stale_appointments(records: list[Appointment], now: datetime, age_days: int = 30) -> list[Appointment]:
    cutoff = now - timedelta(days=age_days)
    return [record for record in records if record.status == "completed" and record.updated_at < cutoff]


def notification_for(record: Appointment) -> dict[str, str]:
    return {
        "event": "appointment_record_archived",
        "appointment_id": record.appointment_id,
        "patient_ref": record.patient_ref,
        "message": "Your appointment record was archived according to the clinic retention schedule.",
    }


def run_sweep(client: InfraiClient, records: list[Appointment], now: datetime) -> dict[str, Any]:
    stale = stale_appointments(records, now)
    for record in stale:
        client.publish(notification_for(record))
    deleted = client.delete_objects("appointment-archive", [record.appointment_id for record in stale]) if stale else {"items": []}
    return {"archived_count": len(stale), "deleted": deleted}


if __name__ == "__main__":
    InfraiClient()
    print("healthtech sweep ready; invoke run_sweep from the configured scheduler")
    print(datetime.now(timezone.utc).isoformat())
