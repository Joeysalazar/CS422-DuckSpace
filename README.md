# What Needs To Be Done

## Current Work

### Joey - Frontend / UI
- Build the main homepage layout.
- Add facility cards for each space.
- Add search and filter tools for space type, day/time, and group size.
- Add a facility detail or analysis view that shows rules, schedule notes, current usage, and next steps.
- Add a simple check-in form with name and group size.
- Show an estimated usage count for each facility.

### Kai - Database
- Continue cleaning up the database schema.
- Make sure the database runs correctly.
- Make sure each facility has a unique facility ID.
- Make sure facility IDs connect correctly to rules, schedules, and check-ins.
- Add or prepare sample database entries for testing.

## Remaining Work

### Backend / Flask
- Create routes that send facility data to the UI.
- Create routes for rules and schedule data.
- Create routes for check-ins and current usage counts.
- Connect the UI to the database instead of hardcoded sample data.
- Make sure the app can run locally without needing private credentials.

### Content / Data
- Choose the first Rec spaces for the demo.
- Add public rules, hours, restrictions, and next-step info for those spaces.
- Add schedule or availability-note data for the selected spaces.
- Keep private or unofficial information out of the app.
- Mark any sample/demo schedule data clearly.

### Check-In / Usage Estimate
- Keep the check-in system simple.
- Do not collect DuckIDs or official student information.
- Use only a name and group size for the demo.
- Use check-ins to estimate how busy a space is, not to create an official reservation system.

### Final Integration
- Merge branches carefully.
- Test the project from a clean clone.
- Update setup instructions.
- Make sure the demo runs without private accounts or credentials.
- Prepare a short demo flow showing search, filters, space analysis, and check-in count.
