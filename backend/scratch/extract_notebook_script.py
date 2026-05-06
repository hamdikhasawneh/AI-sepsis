import json

notebook_path = r'c:\Users\Excalibur\Desktop\AI sepsis\AI-sepsis\notebooks\03b_transformer_only.ipynb'
output_path = r'c:\Users\Excalibur\Desktop\AI sepsis\AI-sepsis\backend\tests\extract_notebook.py'

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

with open(output_path, 'w', encoding='utf-8') as f:
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] == 'code':
            f.write(f"# --- Cell {i} ---\n")
            f.write("".join(cell['source']))
            f.write("\n\n")
