from flask import Flask, render_template, request, redirect, send_file
import pandas as pd
import io
import os
import time

app = Flask(__name__, template_folder='../templates')

# Maximum allowed file size limit in Megabytes (change as needed for testing)
MAX_FILE_SIZE_MB = 5.0
global_processed_df = None  # Temporary cache for report generation

@app.route('/', methods=['GET', 'POST'])
def index():
    global global_processed_df
    table_data = None
    filename = None
    error_message = None
    
    if request.method == 'POST':
        if 'dataset_file' in request.files:
            file = request.files['dataset_file']
            if file.filename != '':
                filename = file.filename
                
                # Check file size limit exception
                file.seek(0, os.SEEK_END)
                file_size_bytes = file.tell()
                file.seek(0)
                file_size_mb = file_size_bytes / (1024 * 1024)
                
                if file_size_mb > MAX_FILE_SIZE_MB:
                    error_message = f"❌ File size exceeds limit! Your file is {file_size_mb:.2f} MB. Maximum allowed limit is {MAX_FILE_SIZE_MB} MB."
                    print(f"[REJECTED] {filename} was {file_size_mb:.2f} MB (Exceeds {MAX_FILE_SIZE_MB} MB limit).")
                    return render_template('index.html', tables=None, filename=None, error=error_message)

                # Start performance timer
                start_time = time.time()
                
                try:
                    file_bytes = file.read()
                    df = pd.read_csv(io.BytesIO(file_bytes), header=None)
                    
                    clean_df = df.dropna(how='all').copy()
                    
                    # Intelligent column detection for Part Number
                    part_col_idx = 2
                    for col in range(clean_df.shape[1]):
                        sample_vals = clean_df.iloc[1:20, col].astype(str).str.strip()
                        if sample_vals.str.contains(r'^[A-Z]{2}\d+', case=False, regex=True).sum() > 2:
                            part_col_idx = col
                            break

                    wo_col = max(0, part_col_idx - 1)
                    desc_col = part_col_idx + 1 if part_col_idx + 1 < clean_df.shape[1] else part_col_idx
                    qty_col = clean_df.shape[1] - 1

                    parsed_df = pd.DataFrame({
                        'work order': clean_df.iloc[:, wo_col].values,
                        'part number': clean_df.iloc[:, part_col_idx].astype(str).str.strip().values,
                        'description': clean_df.iloc[:, desc_col].astype(str).str.strip().values,
                        'quantity': pd.to_numeric(clean_df.iloc[:, qty_col], errors='coerce').fillna(0).values
                    })
                    
                    parsed_df = parsed_df[
                        (parsed_df['part number'] != 'nan') & 
                        (parsed_df['part number'] != '') & 
                        (~parsed_df['part number'].str.lower().str.contains('part|material|物料|工单', na=False))
                    ]
                    
                    parsed_df['prefix'] = parsed_df['part number'].str.slice(0, 2).str.upper()
                    
                    # Aggregate full dataset
                    agg_df = parsed_df.groupby(['prefix', 'part number', 'description'], as_index=False).agg(
                        quantity=('quantity', 'sum'),
                        frequency=('work order', 'nunique'),
                        avg_qty=('quantity', 'mean')
                    )
                    
                    agg_df['avg_qty'] = agg_df['avg_qty'].round(2)
                    
                    # Sort dataset descending by frequency and quantity
                    sorted_agg = agg_df.sort_values(by=['frequency', 'quantity'], ascending=[False, False])
                    
                    # Cache globally for report generation
                    global_processed_df = sorted_agg.copy()
                    table_data = sorted_agg.to_dict(orient='records')
                    
                    # Performance diagnostics log
                    elapsed_time = time.time() - start_time
                    print(f"\n[PERFORMANCE DIAGNOSTIC]")
                    print(f"📁 File: {filename} ({file_size_mb:.2f} MB)")
                    print(f"📊 Processed {len(parsed_df):,} rows into {len(table_data):,} unique aggregated parts.")
                    print(f"⏱️ Total Processing Time: {elapsed_time:.3f} seconds\n")
                    
                except Exception as e:
                    elapsed_time = time.time() - start_time
                    print(f"❌ Error processing file after {elapsed_time:.3f} seconds: {e}")
                    error_message = f"❌ Error processing file format: {e}"
                    table_data = None

    return render_template('index.html', tables=table_data, filename=filename, error=error_message)

@app.route('/download-report')
def download_report():
    global global_processed_df
    if global_processed_df is None or global_processed_df.empty:
        return redirect('/')
    
    try:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet 1: Fast Moving Inventory List (Descending Order)
            export_df = global_processed_df.rename(columns={
                'prefix': 'Prefix Category',
                'part number': 'Part Number',
                'description': 'Description',
                'frequency': 'Work Order Frequency (Distinct WOs)',
                'quantity': 'Total Volume Quantity',
                'avg_qty': 'Average Qty per WO'
            })
            export_df.to_excel(writer, sheet_name='Fast-Moving Inventory', index=False)
            
            # Sheet 2: Prefix Category Breakdown (Dashboard Doughnut Data Equivalent)
            prefix_summary = export_df.groupby('Prefix Category').agg(
                Total_Volume=('Total Volume Quantity', 'sum'),
                Unique_Parts_Count=('Part Number', 'count'),
                Total_Work_Order_Hits=('Work Order Frequency (Distinct WOs)', 'sum')
            ).reset_index().sort_values(by='Total_Volume', ascending=False)
            prefix_summary.to_excel(writer, sheet_name='Prefix Category Breakdown', index=False)

            # Sheet 3: Executive Summary & Narrative Metrics
            summary_data = {
                'Metric Description': [
                    'Total Unique Parts Tracked',
                    'Total Consumed Volume',
                    'Max Part Frequency (Work Orders)',
                    'Dominant Top Prefix Category'
                ],
                'Value': [
                    len(export_df),
                    export_df['Total Volume Quantity'].sum(),
                    export_df['Work Order Frequency (Distinct WOs)'].max(),
                    prefix_summary.iloc[0]['Prefix Category'] if not prefix_summary.empty else 'N/A'
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Executive Summary', index=False)
            
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='Velocity_Inventory_Executive_Report.xlsx'
        )
    except Exception as e:
        print(f"Report generation error: {e}")
        return redirect('/')

@app.route('/convert', methods=['POST'])
def convert_excel_to_csv():
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            try:
                file_bytes = file.read()
                df = pd.read_excel(io.BytesIO(file_bytes))
                
                csv_output = io.StringIO()
                df.to_csv(csv_output, index=False)
                csv_output.seek(0)
                
                base_name = os.path.splitext(file.filename)[0]
                csv_filename = f"{base_name}_converted.csv"
                
                return send_file(
                    io.BytesIO(csv_output.getvalue().encode('utf-8')),
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name=csv_filename
                )
            except Exception as e:
                print(f"Conversion error: {e}")
    return redirect('/')

@app.route('/download-sample')
def download_sample():
    rows = []
    prefixes = ['AB', 'AC', 'AD', 'TR', 'RE', 'IH', 'NM', 'DI', 'CO', 'CA']
    desc_list = ['AB', 'CD', 'EF', 'GH', 'IJ', 'WX', 'KL']
    idx = 1
    
    for wo in range(1000000001, 1000000006):
        for pref in prefixes:
            part_num = f"{pref}{idx:08d}"
            rows.append({
                'index': idx,
                'work order': wo,
                'part number': part_num,
                'description': desc_list[idx % len(desc_list)],
                'quantity': (idx % 30) + 1
            })
            idx += 1
            
    df = pd.DataFrame(rows)
    output = io.BytesIO()
    df.to_csv(output, index=False, header=['', '工单', '物料', '名字', '数量'])
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='sample_dataset.csv'
    )

if __name__ == '__main__':
    app.run(debug=True)
