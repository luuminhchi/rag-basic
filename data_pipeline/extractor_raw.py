import pymupdf4llm

from pathlib import Path

class LegalMarkdownProcess:
    def __init__(self, input_pdf, output_md):
        self.input_pdf = Path(input_pdf)
        self.output_md = Path(output_md)
    
    def pdf_to_markdown(self):
        md_text = pymupdf4llm.to_markdown(str(self.input_pdf))

        self.output_md.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_md, 'w', encoding='utf-8') as f:
            f.write(md_text)
        return md_text

if __name__ == "__main__":
    processor = LegalMarkdownProcess(
        input_pdf="D:\\trafficChatbot_rag\\data\\raw_data\\168_2024_ND-CP_619502.pdf",
        output_md="D:\\trafficChatbot_rag\\data\\processor\\168_2024_ND-CP_619502_raw.md"
    )
    processor.pdf_to_markdown()
    print("Đã chuyển đổi thành công sang file .md!")