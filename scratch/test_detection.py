import zipfile
import xml.etree.ElementTree as ET

DOCX_PATH = r"АРХИТЕКТУРА И ПРЕДВАРИТЕЛЬНАЯ ЭКСПЕРИМЕНТАЛЬНАЯ ОЦЕНКА ПРОТОТИПА ЧАТ.docx"

with zipfile.ZipFile(DOCX_PATH, 'r') as z_in:
    xml_data = z_in.read('word/document.xml')

ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
root = ET.fromstring(xml_data)
body = root.find('w:body', ns)

print("Body has children count:", len(body))

for idx, child in enumerate(body):
    tag = child.tag.split('}')[-1]
    text = ''.join(child.itertext()).strip()
    
    if "АРХИТЕКТУРА И ПРЕДВАРИТЕЛЬНАЯ" in text and idx < 5:
        print(f"[{idx}] Found RU Title: {text[:60]}")
    elif "ОҚУ ДЕРЕКТЕРІНЕ" in text and idx < 5:
        print(f"[{idx}] Found KZ Title: {text[:60]}")
    elif "ARCHITECTURE AND PRELIMINARY" in text and idx < 5:
        print(f"[{idx}] Found EN Title: {text[:60]}")
    elif text == "Аннотация":
        print(f"[{idx}] Found RU Abstract Header")
    elif "Программная реализация выполнена на языке Python" in text:
        print(f"[{idx}] Found Software Stack paragraph")
    elif "Рисунок 1" in text:
        print(f"[{idx}] Found Figure 1: {text}")
    elif "Таблица 1" in text:
        print(f"[{idx}] Found Table 1 Header: {text}")
    elif "Таблица 2" in text:
        print(f"[{idx}] Found Table 2 Header: {text}")
    elif "Генерация графической PNG-карточки" in text:
        print(f"[{idx}] Found Table 2 Discussion: {text[:60]}")
    elif "Таблица 4" in text:
        print(f"[{idx}] Found Table 4 Header: {text}")
    elif text == "Выводы":
        print(f"[{idx}] Found Conclusions Header")

