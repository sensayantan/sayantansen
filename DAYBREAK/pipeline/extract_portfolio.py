"""Extract only ticker symbols from column A of the first XLSX worksheet.
No quantities, balances, account IDs, descriptions or cost basis leave the file.
Python standard library only; workbook is read-only.
"""
import argparse
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

def extract(path):
    ns = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            strings = [''.join(t.text or '' for t in si.findall('.//x:t', ns)) for si in root]
        wb = ET.fromstring(z.read('xl/workbook.xml'))
        sheet = wb.find('x:sheets/x:sheet', ns)
        rid = sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        target = next(r.attrib['Target'] for r in rels if r.attrib['Id'] == rid)
        target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
        root = ET.fromstring(z.read(target))
        symbols = set()
        for c in root.findall('.//x:sheetData/x:row/x:c', ns):
            if not re.fullmatch(r'A\d+', c.attrib.get('r', '')): continue
            v = c.find('x:v', ns)
            value = v.text if v is not None else ''
            if c.attrib.get('t') == 's': value = strings[int(value)]
            elif c.attrib.get('t') == 'inlineStr': value = ''.join(t.text or '' for t in c.findall('.//x:t', ns))
            value = (value or '').strip()
            if re.fullmatch(r'[A-Z][A-Z0-9.-]{0,9}', value) and value not in {'TOTAL','BALANCES','SYMBOL'}:
                symbols.add(value)
    if not symbols: raise ValueError('No ticker symbols found in first-sheet column A')
    return [{'symbol': s} for s in sorted(symbols)]

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('workbook'); p.add_argument('output'); a = p.parse_args()
    out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True)
    data = extract(a.workbook); out.write_text(json.dumps(data, indent=2))
    print(json.dumps({'symbols': len(data), 'output': str(out)}))
