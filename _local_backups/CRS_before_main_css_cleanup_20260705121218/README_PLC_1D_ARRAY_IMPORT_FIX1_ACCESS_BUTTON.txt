CRS PLC 1D Array Import FIX1 + Access Button

Extract this ZIP into the CRS project root and overwrite files.

Run:
  python app.py

Test URLs:
  /plc-array-import/5/12
  /plc-array-import/plc/6
  /plcs
  /plcs/verify/6

Expected:
  The PLC 1D Array Import page opens without 500 error.
  PLC list and PLC verification screen show 1D Array Import access button.

If /plc-array-import/5/12 still gives 500, copy the traceback from the terminal where python app.py is running.
