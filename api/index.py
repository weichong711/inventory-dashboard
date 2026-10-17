from flask import Flask, render_template, request, redirect, send_file
import pandas as pd
import io
import random

app = Flask(__name__, template_folder='../templates')

@app.route('/', methods=['GET', 'POST'])
def index():
    table_data = None
    filename = None
    top_fast = []
    top_slow = []
    
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        
        if file:
            filename = file.filename
            file_bytes = file.read()
            df = pd.read_excel(io.BytesIO(file_bytes))
            
            # Clean column names (strip trailing spaces if any)
            df.columns = df.columns.str.strip()
            
            if 'part number' in df.columns and 'quantity' in df.columns:
                # Group by part number and description to sum up total quantities across work orders
                agg_df = df.groupby(['part number', 'description'], as_index=False)['quantity'].sum()
                
                # Sort descending for Fast-Moving
                fast_df = agg_df.sort_values(by='quantity', ascending=False)
                
                # Sort ascending for Slow-Moving
                slow_df = agg_df.sort_values(by='quantity', ascending=True)
                
                # Assign Velocity Tiers based on cumulative totals or ranking
                total_rows = len(agg_df)
                fast_cutoff = max(1, int(total_rows * 0.2))
                
                # Prepare top lists for charts (Top 10)
                top_fast = fast_df.head(10).to_dict(orient='records')
                top_slow = slow_df.head(10).to_dict(orient='records')
                
                # Full table data for display
                table_data = fast_df.to_dict(orient='records')
            else:
                table_data = df.head(100).to_dict(orient='records')

    return render_template(
        'index.html', 
        tables=table_data, 
        filename=filename,
        top_fast=top_fast,
        top_slow=top_slow
    )

@app.route('/download-sample')
def download_sample():
    prefixes = ['DI', 'NM', 'RE', 'CO', 'IC', 'IH', 'CA', 'TR']
    letters = ['AB', 'CD', 'EF', 'GH', 'IJ', 'KL', 'NM', 'OP', 'QR', 'ST', 'WX']
    
    rows = []
    idx = 1
    for wo in range(1000000001, 1000000021):
        for i in range(10):
            # Format: 2 letters + 8 digits = 10 characters (e.g., DI17627040)
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
