CRS PLC Tag Browser Online Diagnostics FIX3
==========================================

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

Click Diagnostic Browse All.

Expected
--------
If online browse works, controller tag count should be greater than 0 and sample tags should display.
If controller tag count remains 0, manually add the exact recipe array tag name using Manual Add Fallback.
