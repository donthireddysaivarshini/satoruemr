# Satoru EMR — Excel exports

Two read-only exports, run straight against CouchDB. **No CHT rebuild, no
config upload, no server change.** They only ever send `GET` requests.

```
cht-core   (the platform - untouched by this)
satoruemr  (this repo)
  scripts/export_emr.py   <- run this
```

## 1. One-time setup

```bash
pip install -r scripts/requirements.txt      # openpyxl + requests
```

(or with uv: `uv pip install -r scripts/requirements.txt`)

## 2. Point-and-click UI (no commands)

Instead of typing scopes, run the little export page once and use it from a
browser:

```bash
python scripts/export_server.py --url "https://medic:PASSWORD@<HOST>:10443/medic"
```

Open **http://127.0.0.1:8095** — buttons for "all participants", a camp
dropdown, and a participant dropdown, each downloading the same .xlsx the
commands below produce. The CouchDB password stays server-side and is never
sent to the browser. Binds to localhost only; `--host 0.0.0.0` exposes it on
the LAN (trusted networks only).

## 3. The two exports (command line)

### A. Per-participant report  —  `participant-report=<id>`

One workbook for one participant. A `Participant` summary sheet, then one
sheet per completed scale laid out as a readable report:

```
Assessment information   (ID, name, DOB, assessment date, chronological age,
                          disclaimer, trained-worker confirmation)
<age band / domain / section>   Question | Answer | Score     (per group)
...
Scoring results          (raw score, developmental/social quotient, ...)
Notes
Supporting documents
```

```bash
python scripts/export_emr.py \
  --url "https://medic:PASSWORD@<HOST>:10443/medic" \
  --scope participant-report=<participantId> \
  --out ./out
```

### B. Every participant at once (all camps)  —  `all-workbook`

The same layout as the camp workbook, but across **every camp** — one
`Participants` sheet listing all participants, then one sheet per scale with
every assessment. Each sheet gets an extra **`Camp`** column so rows stay
attributable. No ID needed.

```bash
python scripts/export_emr.py \
  --url "https://medic:PASSWORD@<HOST>:10443/medic" \
  --scope all-workbook \
  --out ./out
```

### C. Whole-camp workbook (Kobo-style)  —  `camp-workbook=<id>`

One workbook for one camp. A `Participants` sheet (one row per participant,
with "Scales completed"), then one sheet per scale that was actually done in
the camp (`DDST-II`, `DST`, `MoCA`, `VSMS`) — **one row per assessment**,
human-readable question columns, `<question> - score` columns where the scale
has per-item scores, then the result columns. Participants who didn't do a
scale never appear on its sheet. Screeners/submitters are never listed as
participants.

```bash
python scripts/export_emr.py \
  --url "https://medic:PASSWORD@<HOST>:10443/medic" \
  --scope camp-workbook=<campId> \
  --out ./out
```

### Finding the IDs

CHT People page URL: `.../#/contacts/<ID>` — open the camp or the participant,
copy the trailing UUID. Or Fauxton → `medic` DB → the contact's `_id`.

## 4. Notes

- **Scores are never recalculated.** Stored form results are shown as-is.
- Question labels and choice labels (`yes`→`Yes`, `P`→`Pass`, …) come from the
  form XMLs (`forms/app/*.xml`) via `scale_meta.py` — the same source the CHT
  Reports screen uses, so the export and the on-screen report always match.
- Attachments are listed by filename, not embedded.
- Repeat-group answers are written as JSON in a single cell (lossless).
- Legacy scopes (`all`, `camp=<id>`, `participant=<id>`) still exist for a raw
  dump; the two scopes above are the supported ones.

## 5. Self-check (no server needed)

```bash
python scripts/validate_exports.py       # asserts structure/labels on synthetic docs
python scripts/make_sample_data.py --xlsx ./out/sample   # writes example workbooks to eyeball
```
