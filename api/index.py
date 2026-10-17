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
                    df = pd.read_excel(io.BytesIO(file_bytes))
                    
                    # Clean column names
                    df.columns = df.columns.str.strip()
                    
                    if 'part number' in df.columns and 'quantity' in df.columns:
                        df['prefix'] = df['part number'].astype(str).str[:2].str.upper()
                        agg_df = df.groupby(['prefix', 'part number', 'description'], as_index=False)['quantity'].sum()
                        table_data = agg_df.sort_values(by='quantity', ascending=False).to_dict(orient='records')
                    else:
                        table_data = df.head(100).to_dict(orient='records')
                except Exception as e:
                    print(f"Error: {e}")
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
            
            desc = random.choice(letters)
            qty = random.randint(1, 50)
            
            rows.append({
                'work order': wo,
                'part number': part_num,
                'description': desc,
                'quantity': qty
            })
            idx += 1
            
    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='filled_dataset.xlsx'
    )

if __name__ == '__main__':
    app.run(debug=True)
