CRS PLC Tag Browser UI Polish FIX4
==================================

Apply
-----
Extract this ZIP into the CRS project root and overwrite files.

Run
---
python app.py

Test
----
Open:
/plc-tags/5/12?online_search=1&search=&array_only=0&bool_only=0

Expected
--------
- Search filters align properly.
- Tag result metrics appear in cards.
- Online PLC tags show in a compact scrollable table.
- Use For 1D Import button remains available for array tags.
- Manual Add Fallback is collapsed but available.
