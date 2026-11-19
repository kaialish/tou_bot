import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile(r'АРХИТЕКТУРА И ПРЕДВАРИТЕЛЬНАЯ ЭКСПЕРИМЕНТАЛЬНАЯ ОЦЕНКА ПРОТОТИПА ЧАТ.docx') as z:
    root = ET.fromstring(z.read('word/document.xml'))

ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
body = root.find('w:body', ns)

with open('scratch/all_paragraphs.txt', 'w', encoding='utf-8') as f:
    for idx, child in enumerate(body):
        tag = child.tag.split('}')[-1]
        text = ''.join(child.itertext()).strip()
        f.write(f'=== [{idx}] <{tag}> ===\n{text}\n\n')

print('Dumped all paragraphs to scratch/all_paragraphs.txt')

