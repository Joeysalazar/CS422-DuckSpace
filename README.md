# What Needs To Be Done

## Frontend / UI
- Build the main homepage layout.
- Add a facility list with cards for each space.
- Add search and filter tools.
- Add a facility detail view that shows rules, schedule notes, and next steps.
- Add a simple check-in form with name and group size.
- Show an estimated current usage count for each facility.

## Database
- Make sure the database schema runs correctly.
- Add sample facility data.
- Add rules for each facility.
- Add schedule or availability-note data.
- Make sure each facility ID connects correctly to rules, schedules, and check-ins.

## Backend / Flask
- Create routes that send facility data to the frontend.
- Create routes for rules and schedule data.
- Create routes for check-ins.
- Connect the frontend to the database instead of hardcoded sample data.

## Content / Data
- Pick the first Rec spaces we want in the demo.
- Add public rules, hours, and restrictions for those spaces.
- Keep anything private or unofficial out of the app.

## Final Integration
- Merge everyone’s branches carefully.
- Test the project from a clean clone.
- Update setup instructions.
- Make sure the demo runs without needing private accounts or credentials.