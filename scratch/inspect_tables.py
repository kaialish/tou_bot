import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile(r'АРХИТЕКТУРА И ПРЕДВАРИТЕЛЬНАЯ ЭКСПЕРИМЕНТАЛЬНАЯ ОЦЕНКА ПРОТОТИПА ЧАТ.docx') as z:
    root = ET.fromstring(z.read('word/document.xml'))

ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
body = root.find('w:body', ns)

t1 = body[46]
print("--- Table 1 XML preview ---")
for r_idx, tr in enumerate(t1.findall('w:tr', ns)):
    cells = [(''.join(tc.itertext()).strip()) for tc in tr.findall('w:tc', ns)]
    print(f"Row {r_idx}: {cells}")

t2 = body[65]
print("\n--- Table 2 XML preview ---")
for r_idx, tr in enumerate(t2.findall('w:tr', ns)):
    cells = [(''.join(tc.itertext()).strip()) for tc in tr.findall('w:tc', ns)]
    print(f"Row {r_idx}: {cells}")

