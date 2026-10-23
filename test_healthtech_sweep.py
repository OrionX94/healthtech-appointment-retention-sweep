from datetime import datetime, timezone

from healthtech_sweep import Appointment, stale_appointments


def test_only_completed_records_older_than_retention_window_are_selected():
    now = datetime(2026, 1, 31, tzinfo=timezone.utc)
    records = [
        Appointment("old-done", "p-101", "completed", datetime(2025, 12, 1, tzinfo=timezone.utc)),
        Appointment("recent-done", "p-102", "completed", datetime(2026, 1, 20, tzinfo=timezone.utc)),
        Appointment("old-open", "p-103", "scheduled", datetime(2025, 11, 1, tzinfo=timezone.utc)),
    ]

    selected = stale_appointments(records, now)

    assert [record.appointment_id for record in selected] == ["old-done"]
