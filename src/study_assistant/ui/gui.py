# src/study_assistant/ui/gui.py
import tkinter as tk
from tkinter import scrolledtext, filedialog
from study_assistant.agents import create_study_agent

class GUI: 
    agent = create_study_agent()
    def __init__(self): 
        self.agent = create_study_agent()
        self.previous_response_id = None

    def send_message(self):
        user_input = input_field.get("1.0", tk.END).strip()
        if not user_input:
            return

        # Show thinking indicator
        thinking_label.config(text=f"{self.agent.personality.name} is thinking...")
        thinking_label.pack(pady=5)
        root.update()

        chat.insert(tk.END, f"You: {user_input}\n\n")
        response = self.agent.chat(
            message=user_input, 
            previous_response_id=self.previous_response_id
        )

        content = response.get("content", "(no response)")
        self.previous_response_id = response.get("response_id", None)
        # Hide thinking indicator
        thinking_label.pack_forget()

        chat.insert(tk.END, f"Bob: {content}\n\n")
        chat.see(tk.END)
        input_field.delete("1.0", tk.END)

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF/DOCX", "*.pdf *.docx")])
        if not file_path: 
            return 
        
        chat.insert(tk.END, f"[Selected: {file_path}]\n\n")
        response = self.agent.chat(
            message=f"Analyse the selected document: {file_path}. "
                    "Use list_incoming_files if needed, then the matching reader tool and store triples."
        )
        content = response.get("content", "(processing complete)")
        self.previous_response_id = response.get("response_id", None)
        chat.insert(tk.END, f"Bob: {content}\n\n")
        chat.see(tk.END)

    def main(self):
        global root, chat, input_field, thinking_label
        root = tk.Tk()
        root.title(f"Study Assistant — {self.agent.personality.name}")
        root.geometry("940x760")

        # Chat history – wraps cleanly and supports full copy-paste
        chat = scrolledtext.ScrolledText(root, wrap=tk.WORD, state='normal', height=25, width=110)
        chat.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Thinking indicator (hidden until needed)
        thinking_label = tk.Label(root, text=f"{self.agent.personality.name} is thinking...", fg="blue")

        # Input field – wraps as you type
        input_field = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=5, width=110)
        input_field.pack(padx=10, pady=5, fill=tk.X)

        tk.Button(root, text="Send", command=self.send_message, width=12).pack(side=tk.LEFT, padx=10)
        tk.Button(root, text="Browse Files…", command=self.browse_file, width=15).pack(side=tk.LEFT)

        root.mainloop()

if __name__ == "__main__":
    GUI().main()