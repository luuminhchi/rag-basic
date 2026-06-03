import re
from pathlib import Path
from dataclasses import dataclass

# Fix: dùng [\#\*\s]* thay vì [\#\*]*\s* để ăn cả "## **" trong một lần
RE_CHUONG = re.compile(r'^\s*[\#\*\s]*Chương\s+([IVXLC]+)(.*)?$', re.IGNORECASE)
RE_DIEU   = re.compile(r'^\s*[\#\*\s]*Điều\s+(\d+)\.\s+(.+)') #+ bắt buộc phải có
RE_MUC    = re.compile(r'^\s*[\#\*\s]*Mục\s+(\d+)\.?\s*(.*)$', re.IGNORECASE)

_MD = re.compile(r'[\#\*\_]+')   # dùng để strip ký hiệu markdown khỏi text

 
@dataclass
class ParserArticle:
    doc_id:      str
    chuong:      str
    chuong_name: str
    muc:         str   # số mục, ví dụ "1"
    muc_name:    str   # tên mục
    so:          int   # số điều
    tieu_de:     str
    text:        str


class LegalDocumentParser:
    def __init__(self, doc_id: str):
        self.doc_id = doc_id

    def parser(self, text: str) -> list[ParserArticle]:
        articles = []
        lines = text.splitlines()

        cur_chuong, cur_chuong_name = '', ''
        cur_muc, cur_muc_name       = '', ''
        cur_so, cur_title, cur_lines = 0, '', []

        def flush_dieu():
            if not cur_lines or cur_so == 0:
                return
            body = '\n'.join(cur_lines).strip()
            if body:
                articles.append(ParserArticle(
                    doc_id=self.doc_id,
                    chuong=cur_chuong,
                    chuong_name=cur_chuong_name,
                    muc=cur_muc,
                    muc_name=cur_muc_name,
                    so=cur_so,
                    tieu_de=cur_title,
                    text=body,
                ))

        for line in lines:
            s = line.strip()
            if not s:
                continue 

            # ── Chương
            m = RE_CHUONG.match(s)
            if m:
                flush_dieu()
                cur_so, cur_lines = 0, []
                cur_muc, cur_muc_name = '', ''          
                cur_chuong = m.group(1).upper()
              
                inline_name = _MD.sub('', m.group(2) or '').strip()[:200]
                cur_chuong_name = inline_name  # nếu rỗng → fallback lấy dòng tiếp theo
                continue

            # Tên chương nằm ở dòng riêng (dòng liền sau "## **Chương X**")
            if cur_chuong and not cur_chuong_name:
                # Bỏ qua nếu dòng này là Điều, Mục, hoặc Chương khác
                if not RE_DIEU.match(s) and not RE_MUC.match(s) and not RE_CHUONG.match(s):
                    cur_chuong_name = _MD.sub('', s).strip()[:200]
                    continue

            # ── Mục 
            m = RE_MUC.match(s)
            if m:
                flush_dieu()
                cur_so, cur_lines = 0, []
                cur_muc      = m.group(1)
                cur_muc_name = _MD.sub('', m.group(2) or '').strip()[:200]
                continue

            # ── Điều  
            m = RE_DIEU.match(s)
            if m:
                flush_dieu()
                cur_so    = int(m.group(1))
                cur_title = _MD.sub('', m.group(2)).strip()[:300]   # strip ** khỏi tiêu đề
                cur_lines = [line]
                continue

            if cur_so > 0:
                cur_lines.append(line)

        flush_dieu()
        return articles


def parse_file(input_path: Path, doc_id: str) -> list[ParserArticle]:
    text = input_path.read_text(encoding='utf-8')
    return LegalDocumentParser(doc_id).parser(text)
