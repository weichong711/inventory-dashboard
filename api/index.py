from flask import Flask, render_template, request, redirect
import pandas as pd
import io

app = Flask(__name__, template_folder='../templates')

@app.route('/', methods=['GET', 'POST'])
def index():
    summary_data = None
    filename = None
    
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        
        if file:
            filename = file.filename
            # Read Excel file directly into memory (No Database required)
            file_bytes = file.read()
            df = pd.read_excel(io.BytesIO(file_bytes))
            
            # Standardize column name checks (adjust these strings to match your Excel headers)
            # Expecting columns like: Part_Number, Description, BOM_Usage_Count, etc.
            if 'Part_Number' in df.columns and 'BOM_Usage_Count' in df.columns:
                # Sort by BOM usage frequency descending to isolate fast-moving materials
                sorted_df = df.sort_values(by='BOM_Usage_Count', ascending=False)
                
                # Automatically classify into Velocity Tiers (Pareto principle: Top 20% as Fast)
                total_rows = len(sorted_df)
                fast_cutoff = max(1, int(total_rows * 0.2))
                med_cutoff = max(2, int(total_rows * 0.6))
                
                sorted_df['Velocity_Tier'] = 'Slow'
                sorted_df.iloc[:fast_cutoff, sorted_df.columns.get_loc('Velocity_Tier')] = 'Fast-Moving'
                sorted_df.iloc[fast_cutoff:med_cutoff, sorted_df.columns.get_loc('Velocity_Tier')] = 'Medium-Moving'
                
                summary_data = sorted_df.to_dict(orient='records')
            else:
                # Fallback if columns don't match exactly, display raw head
                summary_data = df.head(100).to_dict(orient='records')

    return render_template('index.html', tables=summary_data, filename=filename)

if __name__ == '__main__':
    app.run(debug=True)
