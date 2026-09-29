import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
class Validator(HTMLParser):
    def __init__(self): super().__init__(); self.stack=[]; self.ids=set()
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key=='id':
                if value in self.ids: raise ValueError('Duplicate id: '+value)
                self.ids.add(value)
        if tag not in VOID: self.stack.append(tag)
    def handle_startendtag(self,tag,attrs): pass
    def handle_endtag(self,tag):
        if not self.stack or self.stack.pop()!=tag: raise ValueError('Unbalanced tag: '+tag)

def validate(directory,archive):
    directory=Path(directory); a=(directory/archive).read_bytes(); b=(directory/'daybreak-latest.html').read_bytes()
    if a!=b: raise ValueError('Archive/latest checksum mismatch')
    text=a.decode(); parser=Validator(); parser.feed(text)
    if parser.stack: raise ValueError('Unclosed tags')
    config=json.loads((Path(__file__).parent/'config.json').read_text())
    headings=re.findall(r'<h2>(.*?)</h2>',text)
    import html
    if [html.unescape(x) for x in headings]!=config['sections']+['Money / Markets']: raise ValueError('Wrong section headings/order')
    counts=[len(re.findall('<tr>',x)) for x in re.findall(r'<tbody>(.*?)</tbody>',text)]
    if counts[:4]!=[5,5,10,10]: raise ValueError('Wrong market table sizes: '+str(counts))
    if any(x in text for x in ['{{','NaN','undefined','Scheduling remains disabled']): raise ValueError('Unrendered or stale content')
    return {'sha256':hashlib.sha256(a).hexdigest(),'tableRows':counts,'html':'valid'}
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('directory'); p.add_argument('archive'); args=p.parse_args()
    print(json.dumps(validate(args.directory,args.archive)))
