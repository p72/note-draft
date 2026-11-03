"""日本銀行「経済・物価情勢の展望（2026年10月）」全文PDFから図表B3-2を切り出す（トリミングのみ、加工なし）。"""
import urllib.request, pdfplumber
URL = 'https://www.boj.or.jp/mopo/outlook/gor2610b.pdf'
req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
open('gor2610b.pdf', 'wb').write(urllib.request.urlopen(req, timeout=60).read())
page = pdfplumber.open('gor2610b.pdf').pages[49]          # 印刷ページ48
page.crop((302, 352, 540, 574)).to_image(resolution=300).save('../../02_boj_b3-2.png')
