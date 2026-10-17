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
    categories = []
    selected_category = request.form.get('category', 'ALL') if request.method == 'POST' else 'ALL'
    
    if request.method == 'POST':
        # Check if file was uploaded or if we are filtering an existing session
        # In a serverless stateless setup, we read from file upload
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            filename = file.filename
            file_bytes = file.read()
            df = pd.read_excel(io.BytesIO(file_bytes))
            
            # Store uploaded data in request / processing
        # Note: Since Vercel is stateless, we process the uploaded file per request.
        # To handle category filtering seamlessly with file upload, we can keep the file processing inline:
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            filename = file.filename
            df = pd.read_excel(io.BytesIO(file.read()))
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            if 'part number' in df.columns and 'quantity' in df.columns:
                # Extract first two letters as prefix category (e.g. IH, NM, CO)
                df['prefix'] = df['part number'].astype(str).str[:2].str.upper()
                
                # Get unique categories for dropdown filter
                categories = sorted(df['prefix'].unique().tolist())
                
                # Filter by selected category if not 'ALL'
                if selected_category and selected_category != 'ALL':
                    filtered_df = df[df['prefix'] == selected_category]
                else:
                    filtered_df = df

                # Aggregate by part number and description
                agg_df = filtered_df.groupby(['prefix', 'part number', 'description'], as_index=False)['quantity'].sum()
                
                # Sort for fast and slow moving
                fast_df = agg_df.sort_values(by='quantity', ascending=False)
                slow_df = agg_df.sort_values(by='quantity', ascending=True)
                
                top_fast = fast_df.head(10).to_dict(orient='records')
                top_slow = slow_df.head(10).to_dict(orient='records')
                table_data = fast_df.to_dict(orient='records')

    return render_template(
        'index.html', 
        tables=table_data, 
        filename=filename,
        top_fast=top_fast,
        top_slow=top_slow,
        categories=categories,
        selected_category=selected_category
    )

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
