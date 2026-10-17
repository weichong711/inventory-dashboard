from flask import Flask, render_template, request, redirect, send_file
import pandas as pd
import io
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
                    
                    # Automatically check file type and read accordingly
                    if filename.endswith('.csv'):
                        df = pd.read_csv(io.BytesIO(file_bytes), header=None)
                    else:
                        df = pd.read_excel(io.BytesIO(file_bytes), header=None)
                    
                    # Map strictly by column position (Index 1 = Work Order, 2 = Part Number, 3 = Description, 4 = Quantity)
                    clean_df = df.iloc[1:].copy()
                    
                    parsed_df = pd.DataFrame({
                        'work order': clean_df.iloc[:, 1].values,
                        'part number': clean_df.iloc[:, 2].astype(str).str.strip().values,
                        'description': clean_df.iloc[:, 3].astype(str).str.strip().values,
                        'quantity': pd.to_numeric(clean_df.iloc[:, 4], errors='coerce').fillna(0).values
                    })
                    
                    # Extract first two letters as category prefix
                    parsed_df['prefix'] = parsed_df['part number'].str[:2].str.upper()
                    
                    # Aggregate quantities to prevent browser freezing
                    agg_df = parsed_df.groupby(['prefix', 'part number', 'description'], as_index=False)['quantity'].sum()
                    
                    table_data = agg_df.sort_values(by='quantity', ascending=False).to_dict(orient='records')
                except Exception as e:
                    print(f"Error processing file: {e}")
                    table_data = None

    return render_template('index.html', tables=table_data, filename=filename)

@app.route('/download-sample')
def download_sample():
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
    # Export as CSV for fast and lightweight handling
    df.to_csv(output, index=False, header=['', '工单', '物料', '名字', '数量'])
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='filled_dataset.csv'
    )

if __name__ == '__main__':
    app.run(debug=True)
