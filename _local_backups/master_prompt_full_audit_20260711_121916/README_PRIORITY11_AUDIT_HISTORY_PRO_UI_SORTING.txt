Priority 11 Add-on: Audit History Professional UI + Sorting

Copy these folders into your CRS project root and overwrite existing files:
- database
- flask_app
- project_docs

Run:
python app.py

Test:
1. Login as ADMIN or ENGINEERING.
2. Open /audit-history.
3. Confirm compact professional filter card.
4. Apply filters.
5. Click table headers to sort.
6. Confirm filters remain active after sorting.

Commit:
git add database flask_app project_docs
git commit -m "Improve audit history UI and add sortable filters"
