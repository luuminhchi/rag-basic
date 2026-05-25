import sys
import time
from pathlib import Path
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parents[1]/'.env'
load_dotenv(env_path)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag import TrafficLawger
from src.vector_db import load_vector_store


def run_interactive_model(qa_store):
    while True:
        try:
            query = input('enter: ').strip()
            if not query:
                continue
            if query.lower() in ['exit', 'quit']:
                print("Tạm biệt!")
                break

            # t0 = time.perf_counter()
            answer = qa_store.ask(query)
            print(answer)
            # elapsed = time.perf_counter() - t0
            # print(f"\n[Trả lời] (Thời gian phản hồi: {elapsed:.2f}s):\n{answer}\n")
            # print("-" * 50)
        except (KeyboardInterrupt, EOFError):
            print("\nĐã thoát chương trình")
            break
        except Exception as e:
            print(f"Lỗi: {e}")

def main():
    try:
        vector = load_vector_store()
        qa_store = TrafficLawger(vector)
    except Exception as e:
        print(f'Error {e}')
        sys.exit(1)
    
    run_interactive_model(qa_store)

if __name__ == '__main__':
    main()