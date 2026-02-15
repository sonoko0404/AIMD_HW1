import pandas as pd

file_path = r'c:\Users\huangqi\OneDrive\Desktop\AIMD_HW1\Evaluation Sheet_v2.xlsx'

try:
    df = pd.read_excel(file_path)
    # Check the first row (which should be R1)
    print(df.iloc[0])
except Exception as e:
    print(f"Error: {e}")
