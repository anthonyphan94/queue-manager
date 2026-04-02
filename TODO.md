# TODO — SMS Marketing Tool

## High Priority (saves money / prevents problems)

- [ ] **Twilio webhook for real-time opt-outs** — Replace the slow 10,000-message scan with a Twilio webhook that instantly records opt-outs to Firestore. Currently scans on every "Load Recipients" click (~5-10 seconds). Webhook would be instant and never miss one. Needs: new POST endpoint for Twilio to call, Firestore `opt_outs` collection, configure webhook URL in Twilio console.

- [ ] **Parallel SMS sending** — Currently sends one SMS at a time (~40 min for 2,400 recipients). Use `asyncio.gather()` with `Semaphore(10)` for 10 concurrent Twilio API calls. Wrap blocking `client.messages.create` in `asyncio.to_thread()`. Would cut send time to ~4 minutes. Files: `twilio_service.py`, `marketing.py` SSE endpoint.

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

## Unfinished / Needs Attention

- [ ] **Google Sheets API** — Verify `sheets.googleapis.com` is enabled on GCP project `mbl-queue-manager`. Was getting PermissionError.

- [ ] **Twilio account status** — Error 30002 (account/messaging service suspended) appeared in Apr 1 logs. Check Twilio console for compliance issues.

- [ ] **Rotate Twilio API key** — The key `SKa6aed...` was exposed in the `backend/.env` file during this session. Create new key in Twilio console, update GCP Secret Manager, revoke old key.

- [ ] **Change default PIN** — Current PIN `0112` is known. Use the Change PIN feature in the app to set a stronger PIN.
