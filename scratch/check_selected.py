import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile(r'АРХИТЕКТУРА И ПРЕДВАРИТЕЛЬНАЯ ЭКСПЕРИМЕНТАЛЬНАЯ ОЦЕНКА ПРОТОТИПА ЧАТ.docx') as z:
    root = ET.fromstring(z.read('word/document.xml'))

ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
body = root.find('w:body', ns)

check_indices = [0, 1, 2, 4, 5, 6, 8, 9, 11, 12, 13, 14, 15, 18, 19, 20, 21, 22, 23, 26, 38, 41, 44, 60, 67, 72, 81, 82]

for idx in check_indices:
    p = body[idx]
    text = ''.join(p.itertext()).strip()
    print(f"=== Paragraph [{idx}] ===")
    print(text)
    print()

