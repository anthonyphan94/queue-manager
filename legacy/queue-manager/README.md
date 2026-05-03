# Legacy: Salon Technician Queue Manager

This folder is a preserved snapshot of the original **Salon Technician Turn
Manager** feature that was stripped from the active application in commit
`6deb132` (Apr 1 2026) when the project was repurposed as an SMS marketing tool.

**These files are NOT active.** They are not imported, built, bundled, or
deployed. They exist here purely as reference / archive so the feature can be
studied or restored later without digging through git history.

## Source

All files were extracted from commit `6deb132^` (parent of the strip commit,
hash `ac9eee2`). Paths mirror their original locations in the repo so they can
be dropped back into place if restoration is ever needed.

## What the feature did

A queue/rotation system for a nail salon. Technicians were ordered by
`queue_position` (1..N) and walk-in clients were assigned to the lowest-
positioned `AVAILABLE` + active technician. When a tech finished a service they
rotated to the back of the queue. Techs could also be put `ON_BREAK` or toggled
offline. The app pushed live queue state to connected clients over WebSocket.

## Layout

```
legacy/queue-manager/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── breaks.py           # POST /techs/break, POST /techs/return
│   │   │   └── technicians.py      # CRUD + assign/complete/skip/reorder
│   │   ├── schemas.py              # Pydantic models for the queue API
│   │   └── services/
│   │       └── turn_rules.py       # Core stateless TurnRulesService
│   ├── tests/                      # pytest suite for the turn logic
│   ├── test_server.py              # smoke-test scripts
│   ├── test_ws.py
│   ├── verify_api.py
│   └── verify_remove.py
├── frontend/
│   ├── src/
│   │   ├── components/TimerDisplay.tsx
│   │   ├── features/dashboard/     # QueueList, WorkingGrid, RestingSection,
│   │   │                           # NextTurnHero, StaffCheckInModal, Icons
│   │   ├── firebase.ts
│   │   ├── hooks/                  # useTurnLogic, useStatusTimer, useBodyScrollLock
│   │   ├── store/techStore.ts
│   │   ├── types/index.ts
│   │   └── views/Dashboard.tsx
│   └── tests/mobile-core.spec.ts   # Playwright e2e for the queue flow
└── _pre_strip_reference/           # Pre-strip copies of files that were
    ├── backend/app/database.py     # MODIFIED (not deleted) in 6deb132.
    ├── backend/app/routers/__init__.py
    ├── backend/main.py             # Useful context for how the queue code
    └── frontend/src/App.tsx        # was wired into the app.
```

## Restoring

If you ever want the feature back on the active path:

1. Copy `legacy/queue-manager/backend/**` over `backend/**`.
2. Copy `legacy/queue-manager/frontend/**` over `frontend/**`.
3. Reconcile `backend/app/database.py`, `backend/main.py`,
   `backend/app/routers/__init__.py`, and `frontend/src/App.tsx` against the
   versions in `_pre_strip_reference/` — these files still exist on the active
   path but had queue code surgically removed.
4. Re-add any frontend deps that were dropped (see `frontend/package.json`
   diff in commit `6deb132`).
5. Restore Firestore schema for the `technicians` collection.
