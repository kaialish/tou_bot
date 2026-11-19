import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile(r'АРХИТЕКТУРА И ПРЕДВАРИТЕЛЬНАЯ ЭКСПЕРИМЕНТАЛЬНАЯ ОЦЕНКА ПРОТОТИПА ЧАТ.docx') as z:
    root = ET.fromstring(z.read('word/document.xml'))

ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
body = root.find('w:body', ns)

for idx in range(25):
    child = body[idx]
    text = ''.join(child.itertext()).strip()
    tag = child.tag.split('}')[-1]
    print(f'[{idx:2d}] <{tag}>: {text}\n')

