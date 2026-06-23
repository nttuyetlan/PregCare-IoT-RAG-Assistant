import json
import re
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

import fitz

BASE = Path('/mnt/data/momcare_rag_dataset')
RAW_DIR = BASE / 'data' / 'raw_pdfs'
EXTRACTED_DIR = BASE / 'data' / 'extracted'
SCRIPTS_DIR = BASE / 'scripts'
SQLITE_DIR = BASE / 'data' / 'sqlite'
CHROMA_DIR = BASE / 'data' / 'chroma_db'
for d in [RAW_DIR, EXTRACTED_DIR, SCRIPTS_DIR, SQLITE_DIR, CHROMA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

PDFS = {
    'ddphunucothai': {
        'src': Path('/mnt/data/ddphunucothai_48201712.pdf'),
        'filename': 'ddphunucothai_48201712.pdf',
        'doc_title': 'Hướng dẫn quốc gia dinh dưỡng cho phụ nữ có thai và bà mẹ cho con bú',
        'doc_type': 'nutrition_guideline',
        'version': '2017',
        'issued_by': 'Bộ Y tế',
        'decision': '776/QĐ-BYT ngày 08/03/2017',
        'default_audience': 'pregnant_mother_or_breastfeeding_mother',
    },
    'dvcsskss': {
        'src': Path('/mnt/data/dvcsskss_48201712.pdf'),
        'filename': 'dvcsskss_48201712.pdf',
        'doc_title': 'Hướng dẫn quốc gia về các dịch vụ chăm sóc sức khỏe sinh sản',
        'doc_type': 'reproductive_health_guideline',
        'version': '2016',
        'issued_by': 'Bộ Y tế',
        'decision': '4128/QĐ-BYT ngày 29/07/2016',
        'default_audience': 'pregnant_mother_family_or_health_worker',
    },
}

# Copy raw PDFs into project folder
for cfg in PDFS.values():
    shutil.copyfile(cfg['src'], RAW_DIR / cfg['filename'])

REPLACEMENTS = {
    '\x00': ' ',
    '\uf0b7': '- ',
    '\uf02b': '+ ',
    '\uf02d': '- ',
    '\uf0fc': '- ',
    '\uf0a7': '- ',
    '\uf020': ' ',
    'Ƣ': 'Ư',
    'ƣ': 'ư',
    'DINH DƢỠNG': 'DINH DƯỠNG',
    'dinh dƣỡng': 'dinh dưỡng',
    'Dinh dƣỡng': 'Dinh dưỡng',
    'TRƢỞNG': 'TRƯỞNG',
    'trƣởng': 'trưởng',
}

def clean_text(text: str) -> str:
    for a, b in REPLACEMENTS.items():
        text = text.replace(a, b)
    text = text.replace('\r', '\n')
    # Remove repeated whitespace but preserve paragraph breaks
    lines = []
    for raw in text.split('\n'):
        line = re.sub(r'[ \t]+', ' ', raw).strip()
        # Remove standalone page numbering artifacts
        if re.fullmatch(r'(\|\s*)?\d{1,4}\s*(\|)?', line):
            continue
        if re.fullmatch(r'[ivxlcdmIVXLCDM]+\s*\|?', line):
            continue
        # Remove leading page number with pipe on header/footer
        line = re.sub(r'^\|\s*\d{1,4}\s*', '', line).strip()
        line = re.sub(r'^\d{1,4}\s*\|\s*', '', line).strip()
        lines.append(line)
    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()
    return text

DANGER_KEYWORDS = [
    'sốc', 'khó thở', 'suy hô hấp', 'trụy tim mạch', 'suy tim', 'chảy máu âm đạo',
    'ra máu', 'co giật', 'hôn mê', 'sốt cao', 'đau bụng dữ dội', 'đau đầu',
    'nhức đầu', 'hoa mắt', 'nhìn mờ', 'phù', 'đái ít', 'thai máy giảm', 'rò nước ối',
    'vỡ ối', 'tăng huyết áp', 'tiền sản giật', 'sản giật', 'băng huyết', 'ngất',
]

def is_red_flag_text(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in DANGER_KEYWORDS)

# Page-level inclusion rules.
# PDF pages are 1-indexed here.
def classify_page(source_id: str, pdf_page: int, text: str):
    low = text.lower()
    include_for_rag = False
    action = 'exclude'
    topic = 'other'
    subtopic = 'general'
    audience = PDFS[source_id]['default_audience']
    section_title = extract_heading(text) or ''

    if source_id == 'ddphunucothai':
        # Keep the useful guideline body. Front matter/TOC are excluded from vector DB but retained in pages.jsonl.
        if pdf_page >= 8:
            include_for_rag = True
            action = 'rag'
            topic, subtopic = infer_nutrition_topic(low, pdf_page)
            audience = 'pregnant_mother_or_breastfeeding_mother'
        else:
            topic = 'front_matter'
            subtopic = 'toc_or_decision'

    elif source_id == 'dvcsskss':
        # Selected user-facing sections only; professional procedures remain excluded.
        if 43 <= pdf_page <= 58:
            include_for_rag = True
            action = 'rag'
            topic = 'cham_soc_truoc_sinh'
            subtopic = infer_dv_subtopic(low, pdf_page)
            audience = 'pregnant_mother'
        elif 84 <= pdf_page <= 92:
            include_for_rag = True
            action = 'rag'
            topic = 'cham_soc_sau_sinh'
            subtopic = infer_dv_subtopic(low, pdf_page)
            audience = 'postpartum_mother_and_newborn'
        elif 219 <= pdf_page <= 220:
            include_for_rag = True
            action = 'rag'
            topic = 'cham_soc_so_sinh'
            subtopic = 'cho_tre_ra_vien_va_theo_doi_tai_nha'
            audience = 'newborn_family'
        elif 226 <= pdf_page <= 228:
            include_for_rag = True
            action = 'rag'
            topic = 'cham_soc_so_sinh'
            subtopic = 'tre_non_thang_nhe_can'
            audience = 'newborn_family'
        elif 229 <= pdf_page <= 233:
            include_for_rag = True
            action = 'rag'
            topic = 'nuoi_con_bang_sua_me_va_kangaroo'
            subtopic = infer_dv_subtopic(low, pdf_page)
            audience = 'breastfeeding_mother_or_newborn_family'
        elif 141 <= pdf_page <= 145:
            include_for_rag = False
            action = 'safety_rule_only'
            topic = 'dau_hieu_nguy_hiem'
            subtopic = 'cap_cuu_san_khoa'
            audience = 'pregnant_mother_or_postpartum_mother'
        elif 3 <= pdf_page <= 7:
            topic = 'table_of_contents'
        else:
            topic = 'excluded_professional_or_unrelated'

    red_flag = is_red_flag_text(text) or action == 'safety_rule_only'
    return {
        'include_for_rag': include_for_rag,
        'action': action,
        'topic': topic,
        'subtopic': subtopic,
        'audience': audience,
        'red_flag': bool(red_flag),
        'section_title': section_title,
    }

def infer_nutrition_topic(low: str, pdf_page: int):
    # ddphunucothai has reliable page ranges after front matter.
    # PDF page 8 roughly equals document page 1.
    if 8 <= pdf_page <= 12:
        return 'tam_quan_trong_dinh_duong', 'vai_tro_dinh_duong'
    if 13 <= pdf_page <= 26:
        if any(x in low for x in ['sắt', 'acid folic', 'folic', 'iod', 'canxi', 'vitamin', 'kẽm', 'dha']):
            return 'nhu_cau_dinh_duong_va_vi_chat', 'vitamin_khoang_chat'
        return 'nhu_cau_dinh_duong', 'nhu_cau_nang_luong_chat_dinh_duong'
    if 27 <= pdf_page <= 30:
        return 'sua_va_che_pham_sua', 'khuyen_nghi_su_dung_sua'
    if 31 <= pdf_page <= 38:
        if any(x in low for x in ['tăng cân', 'bmi', 'thừa cân', 'béo phì']):
            return 'tang_can_va_bmi_thai_ky', 'tang_can_phu_hop'
        return 'che_do_an_thai_ky', 'khau_phan_thuc_pham'
    if 39 <= pdf_page <= 66:
        return 'dinh_duong_benh_ly_thai_ky', 'benh_ly_thai_ky'
    if 67 <= pdf_page <= 72:
        return 'tu_van_dinh_duong', 'ky_nang_va_quy_trinh_tu_van'
    if pdf_page >= 73:
        return 'phu_luc_nhu_cau_dinh_duong', 'bang_nhu_cau_khuyen_nghi'
    return 'dinh_duong_thai_ky', 'general'

def infer_dv_subtopic(low: str, pdf_page: int):
    if 'trước khi có thai' in low:
        return 'tu_van_truoc_khi_co_thai'
    if 'chăm sóc trước sinh' in low or 'khám thai' in low:
        return 'kham_thai_va_cham_soc_truoc_sinh'
    if 'tư vấn cho phụ nữ có thai' in low:
        return 'tu_van_phu_nu_co_thai'
    if 'chẩn đoán trước sinh' in low:
        return 'sang_loc_chan_doan_truoc_sinh'
    if 'quản lý thai' in low:
        return 'quan_ly_thai'
    if 'ngày đầu sau đẻ' in low:
        return 'ngay_dau_sau_de'
    if 'tuần đầu sau đẻ' in low:
        return 'tuan_dau_sau_de'
    if '6 tuần đầu sau đẻ' in low:
        return 'sau_sinh_6_tuan_dau'
    if 'sữa mẹ' in low:
        return 'tu_van_nuoi_con_bang_sua_me'
    if 'kangaroo' in low:
        return 'phuong_phap_kangaroo'
    return 'general'

HEADING_PATTERNS = [
    r'^(PHẦN\s+\d+.*)$',
    r'^([A-ZĐÂĂÊÔƠƯÁÀẢÃẠẤẦẨẪẬẮẰẲẴẶÉÈẺẼẸẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ0-9 ,\-–/()]+)$',
]

def extract_heading(text: str):
    lines = [x.strip() for x in text.split('\n') if x.strip()]
    candidates = []
    for line in lines[:12]:
        if len(line) < 5 or len(line) > 120:
            continue
        # Mostly uppercase or starts with numbered title.
        alpha = [c for c in line if c.isalpha()]
        uppercase_ratio = sum(1 for c in alpha if c.isupper()) / max(1, len(alpha))
        if uppercase_ratio > 0.65 or re.match(r'^\d+(\.\d+)*\.\s+', line):
            if not re.fullmatch(r'[\d\s|]+', line):
                candidates.append(line)
    if candidates:
        return ' '.join(candidates[:2])[:160]
    return ''

# Extract per-page records
pages = []
for source_id, cfg in PDFS.items():
    doc = fitz.open(cfg['src'])
    for page_index in range(len(doc)):
        pdf_page = page_index + 1
        raw_text = doc[page_index].get_text('text')
        cleaned = clean_text(raw_text)
        if len(cleaned) < 40:
            continue
        classif = classify_page(source_id, pdf_page, cleaned)
        record = {
            'id': f'{source_id}_p{pdf_page:04d}',
            'source_id': source_id,
            'pdf_file': cfg['filename'],
            'pdf_page': pdf_page,
            'text': cleaned,
            'char_count': len(cleaned),
            'metadata': {
                'source_id': source_id,
                'doc_title': cfg['doc_title'],
                'doc_type': cfg['doc_type'],
                'version': cfg['version'],
                'issued_by': cfg['issued_by'],
                'decision': cfg['decision'],
                'pdf_file': cfg['filename'],
                'pdf_page_start': pdf_page,
                'pdf_page_end': pdf_page,
                'language': 'vi',
                **classif,
            }
        }
        pages.append(record)

# Write pages.jsonl
pages_path = EXTRACTED_DIR / 'pages.jsonl'
with pages_path.open('w', encoding='utf-8') as f:
    for r in pages:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

# Chunking
CHUNK_SIZE = 1100
OVERLAP = 120
MIN_CHUNK_SIZE = 280

def normalize_for_chunking(text: str) -> str:
    # Preserve headings/paragraph breaks, but remove hard line-wraps that came from PDF layout.
    text = re.sub(r'\n{2,}', '\n\n', text)
    paras = []
    for para in text.split('\n\n'):
        lines = [x.strip() for x in para.split('\n') if x.strip()]
        if not lines:
            continue
        joined = ' '.join(lines)
        joined = re.sub(r'\s+', ' ', joined).strip()
        paras.append(joined)
    return '\n\n'.join(paras)

def split_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    text = normalize_for_chunking(text)
    if len(text) <= chunk_size:
        return [text] if len(text) >= MIN_CHUNK_SIZE else []

    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_size)
        piece = text[start:end]

        if end < n:
            # Prefer to end at paragraph/sentence boundary near the end of the window.
            candidates = [piece.rfind('\n\n'), piece.rfind('. '), piece.rfind('; '), piece.rfind(': ')]
            cut = max(candidates)
            if cut >= int(chunk_size * 0.55):
                piece = piece[:cut + 1]
                end = start + len(piece)

        piece = piece.strip()
        if len(piece) >= MIN_CHUNK_SIZE:
            chunks.append(piece)

        if end >= n:
            break
        start = max(end - overlap, start + 1)

    # Avoid a tiny tail that is mostly duplicate due to overlap.
    if chunks and len(chunks[-1]) < MIN_CHUNK_SIZE:
        chunks.pop()
    return chunks

chunks_all = []
chunks_for_chroma = []
chunks_excluded = []
for p in pages:
    if p['metadata']['action'] == 'exclude':
        # Keep pages-level text but do not chunk excluded sections.
        continue
    chunks = split_text(p['text'])
    for idx, chunk in enumerate(chunks):
        md = dict(p['metadata'])
        md['chunk_index'] = idx
        md['char_count'] = len(chunk)
        md['red_flag'] = bool(is_red_flag_text(chunk) or md.get('action') == 'safety_rule_only')
        md['retrieval_note'] = 'use_for_rag' if md.get('include_for_rag') else 'not_for_rag_use_rule_or_audit_only'
        item = {
            'id': f"{p['source_id']}_p{p['pdf_page']:04d}_c{idx:03d}",
            'text': chunk,
            'metadata': md,
        }
        chunks_all.append(item)
        if md.get('include_for_rag') and md.get('action') == 'rag':
            chunks_for_chroma.append(item)
        else:
            chunks_excluded.append(item)

for name, data in [
    ('chunks_all.jsonl', chunks_all),
    ('chunks_for_chroma.jsonl', chunks_for_chroma),
    ('chunks_excluded_or_safety_only.jsonl', chunks_excluded),
]:
    with (EXTRACTED_DIR / name).open('w', encoding='utf-8') as f:
        for r in data:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

# Safety rules: deterministic layer extracted/normalized from dvcsskss emergency section.
safety_rules = {
    'version': 'momcare_safety_rules_v1',
    'created_at': datetime.now().isoformat(timespec='seconds'),
    'source': {
        'source_id': 'dvcsskss',
        'doc_title': PDFS['dvcsskss']['doc_title'],
        'decision': PDFS['dvcsskss']['decision'],
        'pdf_file': PDFS['dvcsskss']['filename'],
        'pdf_pages_used': [51, 52, 84, 87, 90, 141, 142, 143, 144, 145],
    },
    'policy': {
        'rule_layer_position': 'run_before_rag_and_llm',
        'must_not_do': ['không chẩn đoán bệnh', 'không kê thuốc', 'không hướng dẫn tự xử trí cấp cứu chuyên môn tại nhà'],
        'default_emergency_action': 'khuyên liên hệ bác sĩ hoặc đến cơ sở y tế gần nhất ngay',
    },
    'rules': [
        {
            'id': 'preg_redflag_bleeding',
            'level': 'emergency',
            'category': 'pregnancy_or_postpartum_red_flag',
            'keywords': ['ra máu', 'chảy máu âm đạo', 'xuất huyết âm đạo', 'băng huyết', 'chảy máu sau đẻ'],
            'source_quote_summary': 'Tài liệu liệt kê chảy máu âm đạo/chảy máu sau đẻ là tình huống cấp cứu sản khoa cần phát hiện, xử trí và chuyển tuyến.',
            'response_template': 'Mẹ ơi, ra máu hoặc chảy máu âm đạo trong thai kỳ/sau sinh là dấu hiệu cần được kiểm tra trực tiếp. Mẹ nên liên hệ bác sĩ hoặc đến cơ sở y tế gần nhất ngay.',
        },
        {
            'id': 'preg_redflag_severe_abdominal_pain',
            'level': 'emergency',
            'category': 'pregnancy_or_postpartum_red_flag',
            'keywords': ['đau bụng dữ dội', 'đau bụng nhiều', 'đau quặn bụng', 'đau bụng dưới nhiều'],
            'source_quote_summary': 'Tài liệu liệt kê đau bụng dữ dội là một tình huống cấp cứu sản khoa.',
            'response_template': 'Mẹ ơi, đau bụng dữ dội trong thai kỳ hoặc sau sinh có thể là dấu hiệu nguy hiểm. Mẹ nên đi khám ngay để được kiểm tra an toàn.',
        },
        {
            'id': 'preg_redflag_breathing',
            'level': 'emergency',
            'category': 'respiratory_red_flag',
            'keywords': ['khó thở', 'thở gấp', 'tím tái', 'suy hô hấp', 'đau ngực'],
            'source_quote_summary': 'Tài liệu liệt kê khó thở/suy hô hấp là tình huống cấp cứu, cần đánh giá và xử trí kịp thời.',
            'response_template': 'Mẹ ơi, khó thở, tím tái hoặc đau ngực là dấu hiệu nguy hiểm. Mẹ nên gọi người nhà hỗ trợ và đến cơ sở y tế ngay.',
        },
        {
            'id': 'preg_redflag_seizure_coma',
            'level': 'emergency',
            'category': 'neurological_red_flag',
            'keywords': ['co giật', 'hôn mê', 'lú lẫn', 'không tỉnh', 'mất ý thức'],
            'source_quote_summary': 'Tài liệu liệt kê co giật/hôn mê là cấp cứu sản khoa.',
            'response_template': 'Mẹ ơi, co giật, hôn mê hoặc mất ý thức là tình huống cấp cứu. Gia đình cần đưa mẹ đến cơ sở y tế ngay hoặc gọi cấp cứu.',
        },
        {
            'id': 'preg_redflag_high_fever',
            'level': 'urgent',
            'category': 'infection_or_fever_red_flag',
            'keywords': ['sốt cao', 'sốt 40', 'sốt trên 40', 'sốt nhiều', 'nhiệt độ cao'],
            'source_quote_summary': 'Tài liệu định nghĩa sốt cao là sốt ≥ 40°C và liệt kê sốt cao trong nhóm cấp cứu sản khoa.',
            'response_template': 'Mẹ ơi, sốt cao trong thai kỳ hoặc sau sinh cần được theo dõi cẩn thận. Mẹ nên liên hệ bác sĩ hoặc đi khám sớm, không tự ý dùng thuốc khi chưa có hướng dẫn.',
        },
        {
            'id': 'preg_redflag_preeclampsia_signs',
            'level': 'urgent',
            'category': 'preeclampsia_warning_signs',
            'keywords': ['nhức đầu', 'đau đầu dữ dội', 'hoa mắt', 'nhìn mờ', 'phù', 'đái ít', 'tiểu ít', 'tăng huyết áp'],
            'source_quote_summary': 'Trong tư vấn cho phụ nữ có thai, tài liệu nêu dấu hiệu bất thường như đau bụng, ra máu, nhức đầu, phù, đái ít; các nội dung tiền sản giật/tăng huyết áp nằm trong phần bất thường thai nghén.',
            'response_template': 'Mẹ ơi, đau đầu nhiều, nhìn mờ, phù, tiểu ít hoặc huyết áp tăng có thể là dấu hiệu cần khám sớm trong thai kỳ. Mẹ nên liên hệ bác sĩ để được kiểm tra trực tiếp.',
        },
        {
            'id': 'preg_redflag_shock',
            'level': 'emergency',
            'category': 'shock_or_circulation_red_flag',
            'keywords': ['xanh tái', 'vã mồ hôi', 'chân tay lạnh', 'mạch nhanh', 'huyết áp tụt', 'ngất', 'choáng'],
            'source_quote_summary': 'Tài liệu mô tả sốc sản khoa với các dấu hiệu như xanh tái, vã mồ hôi, chân tay lạnh, mạch nhanh nhỏ, huyết áp hạ.',
            'response_template': 'Mẹ ơi, dấu hiệu choáng, ngất, tay chân lạnh, vã mồ hôi hoặc huyết áp tụt là tình huống nguy hiểm. Gia đình nên đưa mẹ đi cấp cứu ngay.',
        },
        {
            'id': 'postpartum_redflag_lower_abdominal_pain_fever',
            'level': 'urgent',
            'category': 'postpartum_warning_signs',
            'keywords': ['sốt sau sinh', 'đau bụng dưới sau sinh', 'sản dịch hôi', 'đau bụng dưới'],
            'source_quote_summary': 'Phần chăm sóc 6 tuần đầu sau đẻ yêu cầu hỏi các bất thường như sốt và đau bụng dưới.',
            'response_template': 'Mẹ ơi, sốt hoặc đau bụng dưới sau sinh cần được kiểm tra, đặc biệt nếu kèm sản dịch bất thường. Mẹ nên liên hệ cơ sở y tế để được hướng dẫn.',
        },
        {
            'id': 'newborn_redflag_general',
            'level': 'urgent',
            'category': 'newborn_warning_signs',
            'keywords': ['trẻ bỏ bú', 'bú kém', 'khó thở ở trẻ', 'rốn có mủ', 'vàng da nhiều', 'sốt ở trẻ sơ sinh', 'trẻ tím tái'],
            'source_quote_summary': 'Phần chăm sóc sau sinh yêu cầu theo dõi bú mẹ, thở, thân nhiệt, da, rốn và phát hiện tình trạng bệnh lý ở trẻ sơ sinh.',
            'response_template': 'Mẹ ơi, trẻ sơ sinh bú kém, khó thở, tím tái, rốn có mủ, sốt hoặc vàng da nhiều cần được nhân viên y tế kiểm tra sớm.',
        },
    ]
}

safety_json_path = EXTRACTED_DIR / 'safety_rules.json'
safety_json_path.write_text(json.dumps(safety_rules, ensure_ascii=False, indent=2), encoding='utf-8')

# SQLite safety rules DB
sqlite_path = SQLITE_DIR / 'safety_rules.sqlite'
if sqlite_path.exists():
    sqlite_path.unlink()
conn = sqlite3.connect(sqlite_path)
cur = conn.cursor()
cur.execute('''CREATE TABLE safety_rules (
    id TEXT PRIMARY KEY,
    level TEXT NOT NULL,
    category TEXT NOT NULL,
    keywords_json TEXT NOT NULL,
    response_template TEXT NOT NULL,
    source_quote_summary TEXT
)''')
for r in safety_rules['rules']:
    cur.execute('INSERT INTO safety_rules VALUES (?, ?, ?, ?, ?, ?)', (
        r['id'], r['level'], r['category'], json.dumps(r['keywords'], ensure_ascii=False), r['response_template'], r['source_quote_summary']
    ))
conn.commit()
conn.close()

# Write scripts to rerun / build ChromaDB when deps are installed.
(SCRIPTS_DIR / 'build_chroma.py').write_text(r'''import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

BASE = Path(__file__).resolve().parents[1]
CHUNKS_PATH = BASE / 'data' / 'extracted' / 'chunks_for_chroma.jsonl'
CHROMA_DIR = BASE / 'data' / 'chroma_db'
COLLECTION_NAME = 'momcare_knowledge'
EMBED_MODEL_NAME = 'intfloat/multilingual-e5-base'


def batched(items, size=32):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def main():
    rows = [json.loads(line) for line in CHUNKS_PATH.read_text(encoding='utf-8').splitlines() if line.strip()]
    model = SentenceTransformer(EMBED_MODEL_NAME)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={'description': 'MomCare maternal health RAG knowledge base'}
    )

    for batch in tqdm(list(batched(rows)), desc='Indexing ChromaDB'):
        ids = [x['id'] for x in batch]
        docs = [x['text'] for x in batch]
        metadatas = [x['metadata'] for x in batch]
        embeddings = model.encode([f'passage: {d}' for d in docs], normalize_embeddings=True).tolist()
        collection.upsert(ids=ids, documents=docs, metadatas=metadatas, embeddings=embeddings)

    print(f'Indexed {len(rows)} chunks into {CHROMA_DIR}')


if __name__ == '__main__':
    main()
''', encoding='utf-8')

(SCRIPTS_DIR / 'query_chroma.py').write_text(r'''import argparse
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASE = Path(__file__).resolve().parents[1]
CHROMA_DIR = BASE / 'data' / 'chroma_db'
COLLECTION_NAME = 'momcare_knowledge'
EMBED_MODEL_NAME = 'intfloat/multilingual-e5-base'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('question')
    parser.add_argument('--topic', default=None)
    parser.add_argument('--n', type=int, default=5)
    args = parser.parse_args()

    model = SentenceTransformer(EMBED_MODEL_NAME)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(COLLECTION_NAME)
    q_emb = model.encode([f'query: {args.question}'], normalize_embeddings=True).tolist()
    where = {'topic': args.topic} if args.topic else None
    res = collection.query(query_embeddings=q_emb, n_results=args.n, where=where,
                           include=['documents', 'metadatas', 'distances'])
    for i, (doc, meta, dist) in enumerate(zip(res['documents'][0], res['metadatas'][0], res['distances'][0]), start=1):
        print('=' * 80)
        print(f'TOP {i} | distance={dist:.4f} | source={meta.get("source_id")} | topic={meta.get("topic")} | page={meta.get("pdf_page_start")}')
        print(doc[:1200])


if __name__ == '__main__':
    main()
''', encoding='utf-8')

(SCRIPTS_DIR / 'safety_matcher.py').write_text(r'''import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RULES_PATH = BASE / 'data' / 'extracted' / 'safety_rules.json'


def match_safety_rule(text: str):
    rules = json.loads(RULES_PATH.read_text(encoding='utf-8'))['rules']
    low = text.lower()
    matches = []
    for r in rules:
        if any(k.lower() in low for k in r['keywords']):
            matches.append(r)
    order = {'emergency': 0, 'urgent': 1, 'warning': 2}
    matches.sort(key=lambda x: order.get(x['level'], 9))
    return matches


if __name__ == '__main__':
    text = input('Câu hỏi / triệu chứng: ')
    matches = match_safety_rule(text)
    if not matches:
        print('No safety rule matched.')
    else:
        r = matches[0]
        print(f"Matched: {r['id']} | level={r['level']}")
        print(r['response_template'])
''', encoding='utf-8')

(SCRIPTS_DIR / 'ingest_momcare_pdfs.py').write_text((Path('/mnt/data/build_momcare_dataset.py').read_text(encoding='utf-8')), encoding='utf-8')

# requirements
(BASE / 'requirements.txt').write_text('''pymupdf\nchromadb\nsentence-transformers\ntqdm\n''', encoding='utf-8')

# Summary
from collections import Counter, defaultdict
summary = {
    'created_at': datetime.now().isoformat(timespec='seconds'),
    'raw_pdfs': {k: str(RAW_DIR / v['filename']) for k, v in PDFS.items()},
    'counts': {
        'pages_extracted': len(pages),
        'chunks_all': len(chunks_all),
        'chunks_for_chroma': len(chunks_for_chroma),
        'chunks_excluded_or_safety_only': len(chunks_excluded),
        'safety_rules': len(safety_rules['rules']),
    },
    'chunks_for_chroma_by_source': dict(Counter(x['metadata']['source_id'] for x in chunks_for_chroma)),
    'chunks_for_chroma_by_topic': dict(Counter(x['metadata']['topic'] for x in chunks_for_chroma)),
    'note': 'chromadb and sentence-transformers are not installed in the sandbox; run scripts/build_chroma.py after pip install -r requirements.txt to create the persistent ChromaDB folder.',
}
(EXTRACTED_DIR / 'extraction_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

# README
(BASE / 'README.md').write_text(f'''# MomCare RAG Dataset

Gói này đã xử lý 2 PDF Bộ Y tế theo pipeline:

PDF gốc -> trích text theo từng trang -> làm sạch text -> tách theo mục/chủ đề -> chunk nhỏ có metadata -> JSONL kiểm tra -> script đưa vào ChromaDB -> safety rules JSON/SQLite.

## File chính

- `data/extracted/pages.jsonl`: text đã làm sạch theo từng trang của cả 2 PDF.
- `data/extracted/chunks_all.jsonl`: tất cả chunk đã tạo từ vùng được xử lý.
- `data/extracted/chunks_for_chroma.jsonl`: chỉ các chunk nên đưa vào RAG/ChromaDB.
- `data/extracted/chunks_excluded_or_safety_only.jsonl`: chunk không đưa vào RAG, gồm safety-only.
- `data/extracted/safety_rules.json`: rule cảnh báo nguy hiểm chạy trước RAG/LLM.
- `data/sqlite/safety_rules.sqlite`: safety rules dạng SQLite.
- `scripts/build_chroma.py`: tạo ChromaDB persistent từ `chunks_for_chroma.jsonl`.
- `scripts/query_chroma.py`: test retrieval.
- `scripts/safety_matcher.py`: test rule cảnh báo.

## Quy tắc lọc dữ liệu

- `ddphunucothai_48201712.pdf`: lấy phần lớn nội dung thân tài liệu vào RAG vì là hướng dẫn dinh dưỡng cho phụ nữ có thai và bà mẹ cho con bú.
- `dvcsskss_48201712.pdf`: chỉ lấy các phần user-facing: chăm sóc trước sinh, tư vấn phụ nữ có thai, quản lý thai, chăm sóc sau sinh, chăm sóc sơ sinh cơ bản, sữa mẹ/Kangaroo.
- Các dấu hiệu nguy hiểm/cấp cứu sản khoa được tách sang `safety_rules.json` và `safety_rules.sqlite`; không phụ thuộc vào RAG.

## Cách tạo ChromaDB

```bash
cd momcare_rag_dataset
pip install -r requirements.txt
python scripts/build_chroma.py
```

## Test truy xuất

```bash
python scripts/query_chroma.py "Mẹ bầu nên bổ sung sắt và acid folic như thế nào?"
python scripts/query_chroma.py "Sau sinh mẹ cần chăm sóc trẻ sơ sinh ra sao?" --topic cham_soc_sau_sinh
```

## Test safety rule

```bash
python scripts/safety_matcher.py
# nhập: mẹ bị ra máu và đau bụng dữ dội
```

## Thống kê

```json
{json.dumps(summary['counts'], ensure_ascii=False, indent=2)}
```
''', encoding='utf-8')

print(json.dumps(summary, ensure_ascii=False, indent=2))
