import pandas as pd

file = r"D:\gt9088.xls"

df = pd.read_excel(
    file,
    sheet_name="Process Data",
    header=None
)

for i in range(4,15):
    print()
    print("ROW =", i)
    print(df.iloc[i].tolist())