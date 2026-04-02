# TODO — SMS Marketing Tool

## High Priority (saves money / prevents problems)

- [x] **Twilio webhook for real-time opt-outs** — Replaced 10,000-message scan with Firestore `opt_outs` collection + webhook. POST `/marketing/twilio-webhook` records inbound STOP messages instantly. Permanent send failures also auto-recorded. One-time migration via POST `/marketing/seed-opt-outs`.

- [x] **Parallel SMS sending** — `client.messages.create` wrapped in `asyncio.to_thread()`. Batch sends use `Semaphore(10)` + `asyncio.gather()` for 10 concurrent API calls. SSE stream uses `asyncio.Queue` for real-time progress during parallel sends.

- [ ] **Auto-append opt-out footer** — US law (TCPA) requires opt-out instructions in marketing SMS. Auto-append "Reply STOP to unsubscribe" to every broadcast message. Could be a toggle in the UI or always-on. Saves from accidental compliance violations.

- [ ] **Send history / campaign log** — No record of past campaigns. Add Firestore `campaigns` collection storing: message, recipient count, sent/failed, estimated cost, timestamp. Show history in the UI so the user can review what was sent and when.

## Medium Priority (better UX)

- [ ] **Message templates** — Save and reuse message templates (e.g., "Easter promo", "Black Friday"). Firestore `templates` collection with name + body. Dropdown in composer to load a saved template.

- [ ] **Scheduled sending** — Schedule a campaign for a specific date/time instead of sending immediately. Could use Cloud Tasks to enqueue the batch at the scheduled time.

- [ ] **Fix blocking gspread call** — `fetch_phone_numbers()` in `sheets_service.py` is synchronous and blocks the event loop. Wrap in `asyncio.to_thread()` in the `/prepare` endpoint. Same for `fetch_bad_numbers()`.

- [ ] **Cloud Tasks for reliable sending** — Replace the SSE streaming approach with Google Cloud Tasks for bulletproof batch sending. Each SMS becomes a Cloud Task with built-in retry, rate limiting, and crash recovery. Cancel = purge queue. Progress = count completed tasks in Firestore.

## Low Priority (nice to have)

- [ ] **Cost analytics dashboard** — Show total spend per campaign, monthly spend, cost per delivered message. Pull from Twilio usage API or calculate from send results.

- [ ] **Export send results** — Download CSV of send results (name, phone, status, error) after a campaign.

- [ ] **Recipient search/filter** — Search the recipient table by name or phone number when list is large (2,500+ rows).

- [ ] **A/B testing** — Send two message variants to small test groups, then send the winner to the rest.
