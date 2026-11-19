import zipfile
import xml.etree.ElementTree as ET

DOCX_FILE = r"АРХИТЕКТУРА И ПРЕДВАРИТЕЛЬНАЯ ЭКСПЕРИМЕНТАЛЬНАЯ ОЦЕНКА ПРОТОТИПА ЧАТ.docx"

with zipfile.ZipFile(DOCX_FILE, 'r') as z:
    root = ET.fromstring(z.read('word/document.xml'))

ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
body = root.find('w:body', ns)
W_TR = f"{{{ns['w']}}}tr"
W_TC = f"{{{ns['w']}}}tc"

print("=== 1. TITLES ===")
print("RU:", ''.join(body[0].itertext()))
print("KZ:", ''.join(body[1].itertext()))
print("EN:", ''.join(body[2].itertext()))

print("\n=== 2. ABSTRACTS & KEYWORDS ===")
for i in [3, 4, 6, 7, 8, 9, 10, 11, 15]:
    t = ''.join(body[i].itertext()).strip()
    if t:
        print(f"[{i}]: {t[:120]}...")

print("\n=== 3. SOFTWARE STACK ===")
print(''.join(body[38].itertext()))

print("\n=== 4. TABLE 1 (SLOTS) ===")
t1 = body[46]
for r in t1.findall(W_TR):
    cells = [''.join(tc.itertext()).strip() for tc in r.findall(W_TC)]
    print(cells)

print("\n=== 5. TABLE 2 (PERFORMANCE) ===")
t2 = body[65]
for r in t2.findall(W_TR):
    cells = [''.join(tc.itertext()).strip() for tc in r.findall(W_TC)]
    print(cells)

print("\n=== 6. TABLE 2 DISCUSSION ===")
print(''.join(body[67].itertext()))

print("\n=== 7. TABLE 4 (COMPARISON) ===")
t4 = body[74]
for r in t4.findall(W_TR):
    cells = [''.join(tc.itertext()).strip() for tc in r.findall(W_TC)]
    print(cells)

print("\n=== 8. CONCLUSIONS ===")
print("Concl 1:", ''.join(body[81].itertext()))
print("Concl 2:", ''.join(body[82].itertext()))

print("\nVerification complete!")

