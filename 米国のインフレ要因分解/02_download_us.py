"""Archive the published US comparator; this is not a US model re-estimation."""
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import pandas as pd
import requests

URL='https://www.stlouisfed.org/research/pce-inflation-drivers'
class Tables(HTMLParser):
    def __init__(self):
        super().__init__();self.tables=[];self.rows=None;self.row=None;self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='table': self.rows=[]
        if tag=='tr' and self.rows is not None: self.row=[]
        if tag in ['td','th'] and self.row is not None: self.cell=[]
    def handle_data(self,data):
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ['td','th'] and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()));self.cell=None
        if tag=='tr' and self.row is not None:
            self.rows.append(self.row);self.row=None
        if tag=='table' and self.rows is not None:
            self.tables.append(self.rows);self.rows=None

if __name__=='__main__':
    dest=Path(__file__).resolve().parent/'02_data'/'us';dest.mkdir(parents=True,exist_ok=True)
    # 第三者ページの再配布を避けるため、HTML本体は保存せずハッシュと取得日時だけ記録する。
    response=requests.get(URL,timeout=40);response.raise_for_status();payload=response.content
    digest=hashlib.sha256(payload).hexdigest()
    manifest=dest/'manifest.json'
    if manifest.exists():
        if json.loads(manifest.read_text())['sha256']!=digest:
            print('note: page content differs from the archived manifest (page updated since retrieval)')
    else:
        manifest.write_text(json.dumps(dict(url=URL,retrieved_at=datetime.now(timezone.utc).isoformat(),sha256=digest),indent=2)+'\n')
    p=Tables();p.feed(payload.decode('utf-8'))
    table=next(t for t in p.tables if any(r and r[0]=='Inflation (Total)' for r in t))
    if not any(r==['October 2026','October 2025','October 2026','October 2025'] for r in table):
        raise ValueError('Published US dates changed; update column names explicitly')
    data=[r for r in table if len(r)==9 and r[0]]
    pd.DataFrame(data,columns=['component','headline_2026_10_1m','headline_2026_10_3m_ann','headline_2026_10_12m','headline_2025_10_12m','core_2026_10_1m','core_2026_10_3m_ann','core_2026_10_12m','core_2025_10_12m']).to_csv(dest/'published.csv',index=False)
    print('US published table archived; observed columns: October 2026 and October 2025')
