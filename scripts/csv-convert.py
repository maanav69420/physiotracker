import pandas as pd
from pathlib import Path
from tkinter import filedialog
import tkinter as tk

def select_excel_file():
    """Open file dialog to select Excel file"""
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    file_path = filedialog.askopenfilename(
        title="Select Excel File",
        filetypes=[("Excel files", "*.xlsx *.xls")],
        initialdir="."
    )
    
    root.destroy()
    return Path(file_path) if file_path else None

def convert_excel_to_csv(excel_file):
    """Convert Excel sheets to MongoDB-ready CSV files"""
    # Setup output directory
    data_folder = Path(__file__).parent.parent / "data"
    data_folder.mkdir(exist_ok=True)
    
    print(f"Converting: {excel_file.name}")
    
    # Read all sheets
    all_sheets = pd.read_excel(excel_file, sheet_name=None)
    
    converted_files = []
    
    for sheet_name, df in all_sheets.items():
        if df.empty:
            continue
            
        # Clean column names for MongoDB
        df.columns = [
            str(col).strip().lower()
                .replace(' ', '_')
                .replace('-', '_')
                .replace('(', '').replace(')', '')
                .replace('.', '').replace('#', 'num')
            for col in df.columns
        ]
        
        # Handle duplicate column names
        seen = {}
        new_cols = []
        for col in df.columns:
            if col in seen:
                seen[col] += 1
                new_cols.append(f"{col}_{seen[col]}")
            else:
                seen[col] = 0
                new_cols.append(col)
        df.columns = new_cols
        
        # Clean data - fill NaN values
        df = df.fillna('')
        
        # Convert dates to strings
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Create safe filename
        safe_name = "".join(c for c in sheet_name if c.isalnum() or c in '_-').lower()
        csv_file = data_folder / f"{safe_name}.csv"
        
        # Save to CSV
        df.to_csv(csv_file, index=False, encoding='utf-8')
        
        converted_files.append(csv_file)
        print(f"  ✓ {sheet_name} → {csv_file.name} ({len(df)} rows)")
    
    return converted_files

def main():
    print("Excel to MongoDB CSV Converter")
    print("-" * 30)
    
    # Select file
    excel_file = select_excel_file()
    if not excel_file:
        print("No file selected.")
        return
    
    # Convert
    try:
        csv_files = convert_excel_to_csv(excel_file)
        print(f"\n✓ Successfully converted {len(csv_files)} sheets")
        print(f"Files saved to: data/")
        for csv_file in csv_files:
            print(f"  - {csv_file.name}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()