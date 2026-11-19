import zipfile
import shutil
import os
import xml.etree.ElementTree as ET

DOCX_PATH = r"АРХИТЕКТУРА И ПРЕДВАРИТЕЛЬНАЯ ЭКСПЕРИМЕНТАЛЬНАЯ ОЦЕНКА ПРОТОТИПА ЧАТ.docx"
BACKUP_PATH = r"scratch/АРХИТЕКТУРА_ORIGINAL_BACKUP.docx"
UPDATED_PATH = r"scratch/updated_document.docx"

# 1. Create a backup
shutil.copy2(DOCX_PATH, BACKUP_PATH)
print(f"Created backup at {BACKUP_PATH}")

# 2. Extract and inspect document.xml
with zipfile.ZipFile(DOCX_PATH, 'r') as z_in:
    xml_data = z_in.read('word/document.xml')

# Namespaces
ns = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'v': 'urn:schemas-microsoft-com:vml',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'w10': 'urn:schemas-microsoft-com:office:word',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
}

# Register namespaces so ET doesn't change prefixes like w: to ns0:
for prefix, uri in ns.items():
    ET.register_namespace(prefix, uri)

root = ET.fromstring(xml_data)
body = root.find('w:body', ns)
W_P = f"{{{ns['w']}}}p"
W_R = f"{{{ns['w']}}}r"
W_T = f"{{{ns['w']}}}t"
W_PPR = f"{{{ns['w']}}}pPr"
W_RPR = f"{{{ns['w']}}}rPr"
W_TC = f"{{{ns['w']}}}tc"
W_TR = f"{{{ns['w']}}}tr"
W_TBL = f"{{{ns['w']}}}tbl"

def set_p_text(p, text):
    """Replaces the text of paragraph p while preserving its pPr and first rPr styling."""
    pPr = p.find(W_PPR)
    first_r = p.find(W_R)
    first_rPr = None
    if first_r is not None:
        rPr_elem = first_r.find(W_RPR)
        if rPr_elem is not None:
            first_rPr = ET.fromstring(ET.tostring(rPr_elem))
    
    # Remove all children except pPr
    for child in list(p):
        if child != pPr:
            p.remove(child)
            
    # Add new run
    new_r = ET.SubElement(p, W_R)
    if first_rPr is not None:
        new_r.append(first_rPr)
    new_t = ET.SubElement(new_r, W_T)
    new_t.text = text
    # Preserve space if needed
    if text.startswith(' ') or text.endswith(' '):
        new_t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')

def set_cell_text(tc, text):
    """Sets text in a table cell preserving formatting."""
    p = tc.find(W_P)
    if p is None:
        p = ET.SubElement(tc, W_P)
    set_p_text(p, text)

print("Helper functions ready.")

