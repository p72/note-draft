"""Download official CPI and household-total series with the same audit trail."""
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('dh',HERE/'02_dupor_hogan_jp.py')
dh=importlib.util.module_from_spec(spec);spec.loader.exec_module(dh)
if __name__=='__main__':
    for sub in ['official','coverage']:
        dest=HERE/'02_data'/sub
        if dest.exists() and any(dest.iterdir()):
            raise RuntimeError(f'{dest} must be empty to avoid mixing vintages')
    p=dh.get_table('0003427113',raw_dir=HERE/'02_data'/'official',cdTab='1',cdArea='00000',cdCat01='0001,0163')
    p.to_csv(HERE/'02_data'/'official'/'official.csv')
    k=dh.get_table('0004023601',raw_dir=HERE/'02_data'/'coverage',cdCat02='03',cdArea='00000',cdCat01='001100000')
    k.to_csv(HERE/'02_data'/'coverage'/'consumption.csv')
