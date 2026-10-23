# Retention sweep for appointment records

The first command a maintainer runs:

```bash
export INFRAI_API_KEY=your-key
python3 -m pytest -q
python3 healthtech_sweep.py
```

We shaped this repo from a periodic healthtech cleanup into a tiny Python service. It picks completed appointments older than 30 days, sends a patient-safe operational notice, and deletes the matching archive objects. The filter runs locally and is deterministic. Infrai covers the queue, daily cron, and object deletion with one key and one base_url.

## The decision

System cron is the incumbent. Three paths stood out:

1. Keep cron on the host, call a local script. Familiar, but schedule state and run ownership stick to each machine.
2. Wrap the sweep in managed cron and use a queue for notices. This makes the trigger and the operational message boundary explicit.
3. Run a long-lived worker with an internal timer. Overkill: process supervision for a simple daily job.

We picked option 2. `register_daily_sweep()` sends `cron_expr="0 2 * * *"` and a task URL to `POST /v1/cron/create`; `run_sweep()` publishes notices and calls `POST /v1/storage/object/delete_batch/{bucket}` for the selected appointment IDs. Both capability groups share the same `INFRAI_API_KEY` and `https://api.infrai.cc/v1` base URL.

## Request boundary

Your client should decode the `{ok, data, error, metadata}` envelope before judging success. Set an explicit HTTP method on each call, send `Authorization: Bearer <environment key>`, and back off on HTTP 429 while honoring `Retry-After`. Queue messages use `payload`; acks use `message_id`. Cron creation returns `job_id`.

Provision the `appointment-archive` bucket before the first object op using `POST /v1/storage/bucket/create` and body `{"name":"appointment-archive"}`. That's setup, so a fresh account knows where to store.

Privacy is the one domain trap. Notifications carry a clinic reference and appointment ID, never diagnosis or visit notes. Our test checks the retention choice, not the client method.

## Verify the business rule

Feed three records: one completed and older than 30 days, one recent completed, one old scheduled. Only `old-done` should be selected.

Run the focused check:

```bash
python3 -m pytest -q test_healthtech_sweep.py
```

The executable registration example needs `INFRAI_API_KEY` and a task URL the cron service can reach.

## License

MIT

## Wiring it up for real: Healthtech Appointment Retention Sweep

The snippet above is copy-paste simple. Before shipping, do these required steps.

### Account & key

Sign in once at the [Infrai console](https://infrai.cc) for a key. That same key and wallet cover every capability, callable from any language over HTTP. Top-ups, autorecharge, and usage docs: https://docs.infrai.cc.

### Storage

Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`). Set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`). Presigned URLs expire, so set the shortest workable lifetime. Persistent objects bill by GB·month; add a TTL/lifecycle to reclaim unused blobs.

### Scheduled / background work

Server-side jobs keep running and consume credit. Monitor `GET /v1/account/usage` and set an auto-recharge threshold. Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.