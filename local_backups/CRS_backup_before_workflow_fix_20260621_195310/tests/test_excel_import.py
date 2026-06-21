import pandas as pd
import time

print("START")

excel_file = r"D:\gt9088.xls"

start = time.time()

xls = pd.ExcelFile(
    excel_file,
    engine="xlrd"
)

print("OPENED")

print(xls.sheet_names)

print(
    "SECONDS =",
    time.time() - start
)