# My Record — your structured patient record

## What is this?

The **Record** is your personal, digital **health record**: diagnoses,
medications, lab values, allergies, doctor visits, and documents in one place,
cleanly structured and searchable. You can maintain data yourself, **import** it
from official sources, and view trends over time.

> **Important:** This is a personal filing and overview tool, **not a medical
> diagnosis system**. It does not replace professional medical advice.

## The areas (left navigation)

**My Record**
- **Overview** — dashboard with the essentials at a glance.
- **Timeline** — all events chronologically.
- **Diagnoses**, **Medications**, **Lab values**, **Allergies**, **Events**,
  **Imaging**, **Practitioners**, **Documents**, **Notes** — one list each to
  maintain and look up. Lab values can be shown as a **trend curve**.

**Import**
- **eGA / FHIR** — import official health data (see below).

**Tracking**
- **Apple Health** and **Sleep** — trend data from your health tracking.

## Importing data (eGA / FHIR)

You can import your insurer's health record instead of typing everything:

1. In the **TK-Safe app**, **export** your electronic health record (eGA) → you
   get a **ZIP file**.
2. In the import area, upload the **TK-eGA ZIP** (or a **FHIR bundle**).
3. HydraHive reads the data — you see how many entries are **new** and how many
   were **updated**.

**Important:** imported data is **read-only** and stays **separate** from your
self-maintained record. That way official data doesn't mix with your own entries.
The import also shows a **cost overview** (billed doctor visits, pharmacy prices,
your copay) and its own timeline.

## Verifying

Entries can be marked as **manually verified** (checkmark). Unverified entries
(e.g. automatically detected) are flagged accordingly and can be confirmed by
click — so you keep track of what you've personally checked.

## Step by step: add an entry

1. Pick the relevant area on the left (e.g. **Medications**).
2. Add a new entry and fill in the fields.
3. Save. Via the actions you can later **edit**, **delete**, or **verify** entries.

## Common questions

- **"Data could not be loaded"** — connection issue; reload the page.
- **"Where does my import come from?"** — TK-Safe app → export record → upload the
  ZIP here. Without an export there's nothing to import.
- **"Why can't I edit imported entries?"** — They are intentionally read-only
  (fidelity to the original). Add your own details in your own record.

## Tips

- **Import first, then add**: the eGA import saves a lot of typing; add your own
  details afterwards.
- **View lab values as a trend** — curves reveal trends more easily than a table.
- **Use verifying** to distinguish checked from unchecked entries.
