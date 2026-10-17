from flask import Flask, render_template, request, redirect, send_file
import pandas as pd
import io
import os
import random

app = Flask(__name__, template_folder='../templates')

@app.route('/', methods=['GET', 'POST'])
def index():
    table_data = None
    filename = None
    
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                filename = file.filename
                try:
                    file_bytes = file.read()
                    
                    # 1. Automatically handle CSV vs Excel formats
                    if filename.endswith('.csv'):
                        df = pd.read_csv(io.BytesIO(file_bytes), header=None)
                    else:
                        df = pd.read_excel(io.BytesIO(file_bytes), header=None)
                    
                    # 2. Position-based parsing (Ignores language in Header row)
                    # Col B (index 1) = Work Order, Col C (index 2) = Part Number, Col D (index 3) = Description, Col E (index 4) = Quantity
                    clean_df = df.iloc[1:].copy()
                    
                    parsed_df = pd.DataFrame({
                        'work order': clean_df.iloc[:, 1].values,
                        'part number': clean_df.iloc[:, 2].astype(str).str.strip().values,
                        'description': clean_df.iloc[:, 3].astype(str).str.strip().values,
                        'quantity': pd.to_numeric(clean_df.iloc[:, 4], errors='coerce').fillna(0).values
                    })
                    
                    # Extract 2-letter prefix category
                    parsed_df['prefix'] = parsed_df['part number'].str[:2].str.upper()
                    
                    # 3. Server-side pre-aggregation to handle heavy files cleanly
                    agg_df = parsed_df.groupby(['prefix', 'part number', 'description'], as_index=False)['quantity'].sum()
                    table_data = agg_df.sort_values(by='quantity', ascending=False).to_dict(orient='records')
                except Exception as e:
                    print(f"Error processing file: {e}")
                    table_data = None

    return render_template('index.html', tables=table_data, filename=filename)

@app.route('/convert', methods=['POST'])
def convert_excel_to_csv():
    """Built-in Excel to CSV conversion route"""
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
    """Download sample CSV format"""
    prefixes = ['DI', 'NM', 'RE', 'CO', 'IC', 'IH', 'CA', 'TR']
    letters = ['AB', 'CD', 'EF', 'GH', 'IJ', 'KL', 'NM', 'OP', 'QR', 'ST', 'WX']
    
    rows = []
    idx = 1
    for wo in range(1000000001, 1000000021):
        for i in range(10):
            pref = random.choice(prefixes)
            num_str = f"{random.randint(1, 99999999):08d}"
            part_num = f"{pref}{num_str[-8:]}"
            
            rows.append({
                'index': idx,
                'work order': wo,
                'part number': part_num,
                'description': random.choice(letters),
                'quantity': random.randint(1, 50)
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
