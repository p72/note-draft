"""製造業就業者シェアの国際比較。保存CSVから再作図（--refresh でFREDを再取得）。
依存: pandas, matplotlib。日本語フォントをインストールするか JAPANESE_FONT を指定。
"""
from pathlib import Path
import argparse
import os
from urllib.request import urlopen
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = Path(__file__).resolve().parent
COUNTRIES = {'韓国': 'KR', 'イタリア': 'IT', '米国': 'US'}
RAW = BASE / 'international_raw'

def fetch():
    RAW.mkdir(exist_ok=True)
    for country in COUNTRIES.values():
        for prefix in ('LFEAMNTT', 'LFEMTTTT'):
            series = f'{prefix}{country}A647N'
            with urlopen(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}', timeout=60) as response:
                data = response.read()
            if not data.startswith(b'observation_date,'):
                raise ValueError(f'Unexpected CSV: {series}')
            (RAW / f'{series}.csv').write_bytes(data)

def read_series(series):
    data = pd.read_csv(RAW / f'{series}.csv', na_values='.')
    years = pd.to_datetime(data.iloc[:, 0]).dt.year
    assert years.is_unique
    return pd.Series(pd.to_numeric(data.iloc[:, 1]).values, index=years).sort_index()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    if args.refresh:
        fetch()
    font = os.environ.get('JAPANESE_FONT')
    if font:
        font_manager.fontManager.addfont(font)
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=font).get_name()
    else:
        available = {f.name for f in font_manager.fontManager.ttflist}
        names = ['Noto Sans CJK JP', 'IPAexGothic', 'IPAGothic', 'Hiragino Sans', 'Yu Gothic']
        match = next((n for n in names if n in available), None)
        if match is None:
            raise RuntimeError('日本語フォントをインストールするか JAPANESE_FONT を指定してください。')
        plt.rcParams['font.family'] = match
    plt.rcParams['axes.unicode_minus'] = False
    jp = pd.read_csv(BASE / '01_mfg_share.csv', index_col=0)
    out = pd.DataFrame(index=range(1953, 2026))
    fig, ax = plt.subplots(figsize=(12, 7))
    for suffix, style in [('第10回', '-'), ('第11回', '--'), ('第12-14回', ':')]:
        s = jp[f'シェア_{suffix}'].dropna()
        s = s.reindex(range(s.index.min(), s.index.max() + 1))
        out[f'日本_{suffix}'] = s
        ax.plot(s.index, s, color='#24548a', linestyle=style, linewidth=2.6,
                label='日本' if suffix == '第10回' else '_nolegend_')
    for (name, code), color in zip(COUNTRIES.items(), ['#ca6b18', '#148572', '#9c4079']):
        m = read_series(f'LFEAMNTT{code}A647N')
        t = read_series(f'LFEMTTTT{code}A647N')
        pair = pd.concat([m.rename('m'), t.rename('t')], axis=1).dropna().loc[:2025]
        assert (pair.t > 0).all() and (pair.m >= 0).all() and (pair.m <= pair.t).all()
        s = (pair.m / pair.t * 100).reindex(range(pair.index.min(), pair.index.max() + 1))
        out[f'{name}_製造業就業者数_人'] = m
        out[f'{name}_全就業者数_人'] = t
        out[f'{name}_シェア'] = s
        ax.plot(s.index, s, color=color, linewidth=2.4, label=name)
        end = s.dropna().index[-1]
        print(name, s.first_valid_index(), end, 'latest', round(s.loc[end], 3), '2024', round(s.loc[2024], 3))
    ax.set(title='製造業で働く人の割合 ── 日本・韓国・イタリア・米国',
           ylabel='製造業就業者数 ÷ 全産業就業者数（％）', xlim=(1953, 2026), ylim=(0, 32))
    ax.set_xticks([1960, 1970, 1980, 1990, 2000, 2010, 2020, 2025])
    ax.grid(axis='y', alpha=.22)
    ax.spines[['top', 'right']].set_visible(False)
    ax.legend(loc='upper right', ncol=4, frameon=False, fontsize=12)
    fig.text(.08, .09, '年平均・男女計。日本の線種は産業分類の区切り。日本の2011年は欠測のまま表示。', fontsize=9)
    fig.text(.08, .06, '海外は取得できた期間のみ表示。各国の対象年齢・分類改定に差があり、完全な同一定義ではない。', fontsize=9)
    fig.text(.08, .03, '資料：日本＝総務省「労働力調査」（既存CSV）、海外＝OECD Infra-Annual Labor Statistics（FRED経由）', fontsize=9)
    fig.tight_layout(rect=(0, .13, 1, 1))
    fig.savefig(BASE.parent / '02_chart_international.png', dpi=180)
    out.index.name = '年'
    out.to_csv(BASE / '02_international_share.csv', encoding='utf-8-sig', float_format='%.6f')

if __name__ == '__main__':
    main()
