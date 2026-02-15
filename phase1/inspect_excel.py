import pandas as pd
import os

file_path = r'c:\Users\huangqi\OneDrive\Desktop\AIMD_HW1\Evaluation Sheet.xlsx'

try:
    # Load the Excel file
    xls = pd.ExcelFile(file_path)
    
    print("Sheet names:", xls.sheet_names)
    
    # Read the first sheet
    df = pd.read_excel(xls, sheet_name=0)
    
    print("\nColumns in first sheet:")
    print(df.columns.tolist())
    
    print("\nFirst few rows:")
    print(df.head())
    
except Exception as e:
    print(f"Error: {e}")
