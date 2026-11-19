import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile(r'АРХИТЕКТУРА И ПРЕДВАРИТЕЛЬНАЯ ЭКСПЕРИМЕНТАЛЬНАЯ ОЦЕНКА ПРОТОТИПА ЧАТ.docx') as z:
    root = ET.fromstring(z.read('word/document.xml'))

ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
body = root.find('w:body', ns)

keywords = ['pillow', 'png', 'карточк', 'растриз', 'растериз', 'переведи', 'таблица 1', 'таблица 2', '132', 'графическ', 'генерация']

for idx, child in enumerate(body):
    text = ''.join(child.itertext()).strip()
    tag = child.tag.split('}')[-1]
    for kw in keywords:
        if kw in text.lower():
            print(f'=== Element {idx} [{tag}] matched "{kw}": ===')
            print(text[:400])
            print('-' * 40)
            break

