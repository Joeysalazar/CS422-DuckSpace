# Integration Notes

## Current Working Pieces

### UI
- Main UI is on `main`.
- It currently uses mock data in `app.py`.
- UI includes space cards, filters, group size, noise level, and analysis panel.

### Backend/API
- Kai's backend is on the `Kai` branch under `test_db/implementation`.
- API routes tested:
  - `/api/facilities`
  - `/api/facilities/<facility_id>/rules`
  - `/api/facilities/<facility_id>/schedule`
- Backend works, but needs demo data.

### Seed Data
- Robert is working on a seed file.
- Seed data should include facilities, rules, schedules, hours, and possibly sample check-ins.

## Needed Before Integration

- Confirm final facility fields.
- Add demo data for Rec, study, meeting, and social spaces.
- Decide whether database should include:
  - `category`
  - `noise_level`
  - `next_step`
- Decide final check-in structure:
  - name
  - group size
  - facility ID
  - active/expired status
- Avoid DuckIDs or official student data.

## Integration Plan

1. Merge backend/API files into an integration branch.
2. Add final requirements to `requirements.txt`.
3. Replace UI mock data with API data.
4. Connect analysis panel to:
   - facility data
   - rules
   - schedule
   - active check-in counts
5. Test from a clean clone.