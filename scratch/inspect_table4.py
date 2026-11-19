import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile(r'АРХИТЕКТУРА И ПРЕДВАРИТЕЛЬНАЯ ЭКСПЕРИМЕНТАЛЬНАЯ ОЦЕНКА ПРОТОТИПА ЧАТ.docx') as z:
    root = ET.fromstring(z.read('word/document.xml'))

ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
body = root.find('w:body', ns)

t4 = body[74]
print("--- Table 4 XML preview ---")
for r_idx, tr in enumerate(t4.findall('w:tr', ns)):
    cells = [(''.join(tc.itertext()).strip()) for tc in tr.findall('w:tc', ns)]
    print(f"Row {r_idx}: {cells}")

