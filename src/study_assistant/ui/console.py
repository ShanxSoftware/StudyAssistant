# src/study_assistant/ui/console.py
import sys
import time
from study_assistant.config import XAI_API_KEY, DB_PATH, INCOMING_FOLDER
from xaihandler import xAI_Handler
from xaihandler.personality import AgentPersonality, Archetype
from xaihandler.memorystore import MemoryStore
from xaihandler.definitions import AutonomousOutput, JOB_STATUS, JobCard, BatchStatus
from study_assistant.agents import create_study_agent
from study_assistant.tools import common, pdf_reader, word_reader, discovery
from pathlib import Path
import itertools
from contextlib import contextmanager

@contextmanager
def progress_spinner(message: str = "Bob is analysing chunks"):
    """Simple console spinner for long operations. Non-blocking."""
    spinner = itertools.cycle(['|', '/', '-', '\\'])
    stop = False

    def spin(): 
        while not stop: 
            sys.stdout.write(f"\r{message} {next(spinner)} ")
            sys.stdout.flush()
            time.sleep(0.15)
    
    import threading
    spinner_thread = threading.Thread(target=spin, daemon=True)
    spinner_thread.start()

    try: 
        yield
    finally: 
        stop = True
        spinner_thread.join()
        sys.stdout.write("\r" + " " * (len(message) + 10) + "\r") # clear line
        sys.stdout.flush()

def main():
    agent = create_study_agent(name="Bob")

    print(f"Study Assistant - {agent.personality.name} is ready.")
    print("Type your message and press Enter. 'exit', 'quit'. or Ctrl+C to leave.\n")

    previous_response_id = ""
    while True: 
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("exit", "quit", "q"): 
                print("\nGoodbye.")
                break

            if not user_input:
                continue

            # Optional simple commands
            if user_input.startswith("/"):
                if user_input.lower() in ("/clear", "/reset"):
                    # agent.reset() # TODO: Implement method that starts new conversation instance 
                    previous_response_id = "" # Should force new conversation
                    # TODO: Clear the current screen
                    continue
                elif user_input.lower() == "/status": 
                    print(f"Model: {agent.model}")
                    print(f"Memory path: {agent.memory.db_path}")
                    # TODO: Add Token Usage and Budget Remaining details later
                    continue
                elif user_input.lower().startswith("/analyse "):
                    file_path = Path(user_input[9:].strip())
                    if file_path.suffix.lower() == ".pdf": 
                        document = pdf_reader.read_pdf(file_path=file_path, chunk_index=0, reset=False)
                        chunk_index: int = 0
                        while chunk_index <= document["total_chunks"] and document["status"] == "next_chunk":
                            print(f"\nChunk: {chunk_index}")
                            print(f"\n{document["chunk"]}")
                            print(f"\nStatus: {document["status"]}")
                            document = pdf_reader.read_pdf(file_path=file_path, chunk_index=chunk_index, reset=False)
                            chunk_index = chunk_index + 1
                    elif file_path.suffix.lower() == ".docx":
                            document = word_reader.read_docx(file_path=file_path, chunk_index=0, reset=False)
                            chunk_index: int = 0
                            while chunk_index <= document["total_chunks"] and document["status"] == "next_chunk":
                                print(f"\nChunk: {chunk_index}")
                                print(f"\n{document["chunk"]}")
                                print(f"\nStatus: {document["status"]}")
                                document = word_reader.read_docx(file_path=file_path, chunk_index=chunk_index, reset=False)
                                chunk_index = chunk_index + 1
                    print("Chunk retrieval complete\n")
                    
                elif user_input.lower().startswith("/list_incoming"): 
                    pdf_list = list_incoming_pdfs.list_incoming_pdfs()
                    word_list = list_incoming_pdfs.list_incoming_docx()
                    print("\nHere is the list of PDFs in the incomming folder:\n")
                    for p in pdf_list["available_pdfs"]: 
                        print(f"{p}\n")
                    print("\nHere is the list of Word Documents in the incoming folder:\n")
                    for p in word_list["available_docx"]: 
                        print(f"{p}\n")
            else: 
                with progress_spinner(""):
                    if previous_response_id == "":
                        response = agent.chat(message=user_input)
                    else:
                        response = agent.chat(message=user_input, previous_response_id=previous_response_id)
                    content = response.get("content", "(no content)")
                    previous_response_id = response.get("response_id", "")
                print(f"{agent.personality.name}: {content}\n")
        except KeyboardInterrupt: 
            print("\n\nGoodbye.")
            sys.exit(0)
        except Exception as e:
            print(f"\nError: {str(e)}\n")