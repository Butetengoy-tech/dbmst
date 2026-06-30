import pandas as pd
import io

try:
    df = pd.DataFrame(columns=[
        'Competition', 'Swimmer', 'Event', 'Category & Stroke', 'Time', 'Date'
    ])
    df.loc[0] = ['National Championships', 'Michael Phelps', '50m', 'Individual - Freestyle', '00:00:25.50', '2024-08-15']
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
