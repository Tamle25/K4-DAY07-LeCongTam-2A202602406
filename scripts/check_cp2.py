
import csv
import re
import sys
from pathlib import Path

def check_checkpoint2(data_dir="data/ChinhSachDoiTraBaoHanh"):
    D = Path(data_dir)
    if not D.exists():
        print(f"Directory '{data_dir}' does not exist!")
        return

    REQ = ['doc_id', 'title', 'source_url', 'retrieved_at', 'document_version', 'audience']
    mds = sorted(D.glob('*.md'))
    sources_file = D / 'sources.csv'
    
    if not sources_file.exists():
        print("Missing sources.csv file!")
        return

    rows = list(csv.DictReader(open(sources_file, encoding='utf-8')))
    ids = []
    auds = {}
    
    print("\n================ CHECKPOINT 2 VERIFICATION ================")
    for p in mds:
        content = p.read_text(encoding='utf-8')
        parts = content.split('---')
        if len(parts) < 3:
            print(f"{p.name:45} -> THIEU YAML FRONTMATTER")
            continue
            
        fm = dict(re.findall(r'^(\w+):\s*(.+)$', parts[1], re.M))
        doc_id = fm.get('doc_id')
        ids.append(doc_id)
        
        aud = fm.get('audience')
        if aud:
            auds[aud] = auds.get(aud, 0) + 1
            
        is_ok = all(k in fm for k in REQ) and doc_id == p.stem
        status = "OK" if is_ok else "THIEU METADATA HOAC SAI DOC_ID"
        print(f"{p.name:45} -> {status}")

    csv_ids = sorted(r['doc_id'] for r in rows)
    md_ids = sorted(ids)
    csv_status = "KHOP 1-1" if csv_ids == md_ids else "LECH"

    print("-" * 59)
    print(f"So file .md     : {len(mds)} (Can 5-10 file)")
    print(f"Doi chieu CSV   : {csv_status}")
    print(f"Nhom Audience   : {auds}")
    print("===========================================================\n")

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "data/ChinhSachDoiTraBaoHanh"
    check_checkpoint2(target_dir)
