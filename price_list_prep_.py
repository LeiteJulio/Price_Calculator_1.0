import pandas as pd
import glob
import os


def prepare_master_data(input_folder="Price Lists", output_file="master_rates.csv"):
    all_processed_rows = []

    # 1. Gather all Excel files from the folder
    file_paths = glob.glob(os.path.join(input_folder, "*.xlsx"))

    if not file_paths:
        print(f"❌ No .xlsx files found in '{input_folder}'.")
        return

    for path in file_paths:
        # Expected filename format: "DSV-202601.xlsx"
        filename = os.path.basename(path).replace(".xlsx", "")

        if "-" in filename:
            try:
                # Split only once at the last hyphen to handle names like "ABC-Logistics-202601"
                parts = filename.rsplit("-", 1)
                supplier = parts[0]
                file_month = parts[1]  # This is your YYYYMM

                print(f"🔄 Processing: {supplier} for month {file_month}...")

                # Load the 'France' sheet, skipping 39 rows of headers
                df = pd.read_excel(path, sheet_name='France', skiprows=39)

                # Clean: Remove rows that don't have a container type
                df = df[df['Container Type'].notna()]

                for _, row in df.iterrows():
                    # Flatten into 3 modes per row as per your template
                    for mode in ['Barge', 'Road', 'Rail']:
                        entry = {
                            # Metadata
                            'Supplier': supplier,
                            'File_Month': file_month,  # The new YYYYMM column
                            'Origin_Country': row.get('Place of Receipt\nCountry', 'N/A'),
                            'Origin_City': row.get('Place of Receipt City/Port', 'N/A'),
                            'Dest_Country': row.get('Place of Delivery\nCountry', 'N/A'),
                            'Destination': row.get('Place of Delivery\nCity', 'N/A'),
                            'Container': row.get('Container Type', 'N/A'),
                            'Incoterms': row.get('Incoterms', 'N/A'),
                            'Mode': mode,

                            # Origin Zone (Pre-carriage)
                            'O_Curr': row.get('Origin Costs - Currency', 'EUR'),
                            'O_Cost_NonHaz': row.get(f'Total Origin Costs per Container ({mode} Pre-carriage) non-haz',
                                                     0),
                            'O_Cost_Haz': row.get(f'Total Origin Costs per Container ({mode} Pre-carriage) haz', 0),

                            # Ocean Zone (Freight)
                            'Sea_Curr': row.get('Ocean Costs  - Currency', 'USD'),
                            'Sea_Base': row.get('Total Ocean Costs per Container', 0),
                            'Sea_IMO': row.get('Ocean IMO Surcharge (when applicable)', 0),

                            # Destination Zone (On-carriage)
                            'D_Curr': row.get('Destination Costs - Currency', 'EUR'),
                            'D_Cost_NonHaz': row.get('Total Destination Costs per Container non-haz', 0),
                            'D_Cost_Haz': row.get('Total Destination Costs per Container haz', 0),

                            # Logistics Info
                            'Transit_Days': row.get('Transit Time (Days) POL to POD', 'N/A'),
                            'Validity': row.get('Price Validity', 'N/A'),  # The validity from inside the file
                            'Carrier': row.get('Carrier', 'N/A'),
                            'Comments': row.get('Comments', '')
                        }
                        all_processed_rows.append(entry)

            except Exception as e:
                print(f"❌ Error in {filename}: {e}")
        else:
            print(f"⚠️ Skipping {filename}: Filename must be 'Supplier-YYYYMM'")

    # 2. Save the final master file
    if all_processed_rows:
        master_df = pd.DataFrame(all_processed_rows).fillna(0)
        master_df.to_csv(output_file, index=False)
        print(f"\n✅ Success! Master file created with {len(master_df)} quotes.")
    else:
        print("🛑 No data was processed. Check your file names.")


if __name__ == "__main__":
    prepare_master_data()