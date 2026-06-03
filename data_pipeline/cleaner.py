import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

MULTI_BLANK = re.compile(r'\n{3,}')
TAB_PATTERN = re.compile(r'\t+')

CHUONG_I_PATTERN = re.compile(r'Chương\s+I', re.IGNORECASE)
STOP_PATTERN = re.compile(r'Chương\s+IV', re.IGNORECASE)

# STOP_PATTERN = re.compile(
#     r'Nơi\s*nhận|TM\.\s*CHÍNH\s*PHỦ',
#     re.IGNORECASE
# )


def clear_document(raw_text: str) -> str:
    raw_text = TAB_PATTERN.sub(' ', raw_text)
    lines = raw_text.splitlines()

    # BƯỚC 1: Tìm dòng bắt đầu "Chương I"
    start_idx = next(
        (i for i, line in enumerate(lines) if CHUONG_I_PATTERN.search(line)),
        None,
    )
    if start_idx is None:
        log.warning("Không tìm thấy 'Chương I' trong văn bản.")
        return raw_text.strip()


    content_lines = []
    for line in lines[start_idx:]:
        if STOP_PATTERN.search(line):
            log.info("Dừng tại dòng chứa: %s", line.strip())
            break
        content_lines.append(line)

    # BƯỚC 3: Nén khoảng trống thừa
    body_text = "\n".join(content_lines)
    return MULTI_BLANK.sub('\n\n', body_text).strip()


def clear_text(input_path: Path, output_path: Path) -> int:
    raw = input_path.read_text(encoding='utf-8')
    cleaned = clear_document(raw)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(cleaned, encoding='utf-8')
    return len(cleaned.splitlines())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    input_file = Path('D:\\trafficChatbot_rag\\data\\processor\\168_2024_ND-CP_619502_raw.md')
    output_file = Path('D:\\trafficChatbot_rag\\data\\processor\\168_2024_ND-CP_619502.md')

    if input_file.exists():
        total_lines = clear_text(input_path=input_file, output_path=output_file)
        print(f'Clear thành công! File mới bắt đầu từ Chương I và có {total_lines} dòng sạch.')
    else:
        print(f'Không tìm thấy file nguồn tại: {input_file}')
