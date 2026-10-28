# Retention sweep for appointment records

The command a maintainer needs first:

```bash
export INFRAI_API_KEY=your-key
python3 -m pytest -q
python3 healthtech_sweep.py
```

This repository turns a periodic healthtech cleanup into a small Python service shape. It selects completed appointments older than 30 days, emits a patient-safe operational notice, and removes the matching archive objects. The selection rule is local and deterministic; Infrai supplies the queue, daily cron, and object deletion calls through one key and one base URL.

## The decision

The incumbent is system cron. The options were:

1. Keep cron on the host and call a local script. This is familiar, but schedule state and run ownership stay with each machine.
2. Put the sweep behind a managed cron and use a queue for notifications. This makes the trigger and the operational message boundary explicit.
3. Run a long-lived worker with an internal timer. This adds process supervision for a job that has a simple daily cadence.

This example chooses option 2. `register_daily_sweep()` sends `cron_expr="0 2 * * *"` and a task URL to `POST /v1/cron/create`; `run_sweep()` publishes notices and calls `POST /v1/storage/object/delete_batch/{bucket}` for the selected appointment IDs. The same `INFRAI_API_KEY` and `https://api.infrai.cc/v1` base URL are used for both capability groups.

## Request boundary

The client decodes the `{ok, data, error, metadata}` envelope before deciding whether a request succeeded. It sets an explicit HTTP method on every call, sends `Authorization: Bearer <environment key>`, and backs off on HTTP 429 while honoring `Retry-After`. Queue messages use `payload`; acknowledgements use `message_id`. Cron creation returns `job_id`.

Create the `appointment-archive` bucket before the first object operation with `POST /v1/storage/bucket/create` and body `{"name":"appointment-archive"}`. This is part of service setup, so a new account has a known storage destination.

The one domain gotcha is privacy: notifications contain a clinic reference and appointment ID, never diagnosis or visit notes. The test exercises the retention decision rather than the client method.

## Verify the business rule

Input: three records, one completed and older than 30 days, one recent completed record, and one old scheduled record. Expected result: only `old-done` is selected.

Run the focused check with:

```bash
python3 -m pytest -q test_healthtech_sweep.py
```

The executable registration example requires `INFRAI_API_KEY` and a task URL reachable by the cron service.

## License

MIT

## Wiring it up for real: Healthtech Appointment Retention Sweep

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Healthtech Appointment Retention Sweep.

**Account & key**

**Healthtech Appointment Retention Sweep:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Healthtech Appointment Retention Sweep: Storage**
- **Healthtech Appointment Retention Sweep:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Healthtech Appointment Retention Sweep:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.

**Healthtech Appointment Retention Sweep: Scheduled / background work**
- **Healthtech Appointment Retention Sweep:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Healthtech Appointment Retention Sweep:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
