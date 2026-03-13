# /src/study_assistant/ui/gui.py
import dearpygui.dearpygui as dpg
from study_assistant.agents import create_study_agent
from study_assistant.config import DATA_DIR, INCOMING_FOLDER
agent = create_study_agent() # Reuses personality, memory, budget, tools

def send_callback(sender, app_data): 
    user_input = dpg.get_value("input_field").strip()
    if not user_input: 
        return
    
    # Show spinner
    dpg.set_value("spinner_text", "Bob is thinking")
    dpg.show_item("spinner_text")
    dpg.split_frame()  # force immediate redraw

    # Append user message
    current = dpg.get_value("chat_output") or ""
    dpg.set_value("chat_output", current + f"\nYou: {user_input}\n")

    #call agent (same as console)
    response = agent.chat(message=user_input)
    content=response.get("content", "(no response)")
    dpg.hide_item("spinner_text")
    dpg.set_value("chat_output", dpg.get_value("chat_output") + f"{agent.personality.name}: {content}\n\n")
    dpg.set_value("input_field", "")

def browse_callback(sender, app_data, user_data):
    
    #app_data is list of dropped paths
    selected = app_data.get("file_path_name")
    #Trigger analysis via agent (list_incoming_files already registered)
    dpg.set_value("chat_output", dpg.get_value("chat_output") + f"\n[File Selected: {selected}]\n")
    dpg.set_value("spinner_text", "Bob is analysing document")
    dpg.show_item("spinner_text")
    dpg.split_frame()
    response = agent.chat(message=f"Analyse the dropped document: {selected}. Use approrirate reader and store triples.")
    content = response.get("content", "(processing complete)")
    dpg.set_value("chat_output", dpg.get_value("chat_output") + f"{agent.personality.name}: {content}\n\n")
    dpg.hide_item("file_dialog")
    dpg.hide_item("spinner_text")

dpg.create_context()

with dpg.window(label=f"Study Assistant - {agent.personality.name}", tag="main_window", width=920, height=720):
    dpg.add_text(f"Chat with {agent.personality.name} - Your indespensible study assistant")
    dpg.add_input_text(tag="chat_output", multiline=True, readonly=True, width=900, height=480)
    dpg.add_text("Bob is thinking", tag="spinner_text", color=(100, 200, 255), show=False)
    dpg.add_separator()
    dpg.add_text("Type message or select a PDF/DOCX:")
    dpg.add_input_text(tag="input_field", multiline=True, width=900, height=80)
    dpg.add_button(label="Send", callback=send_callback, width=120)
    # Drag-drop zone
    with dpg.group(horizontal=True):
        dpg.add_button(label="Brows Files...", callback=lambda s, a: dpg.show_item("file_dialog"))
        
    with dpg.file_dialog(tag="file_dialog", directory_selector=False, show=False, callback=browse_callback, width=700, height=500):
        dpg.add_file_extension("PDF files (*.pdf){.pdf}", color=(0, 255, 0, 255))
        dpg.add_file_extension("Word Files (*.docx){.docx}", color=(0, 120, 255, 255))
        dpg.add_file_extension("", color=(255, 255, 255, 255)) # all files fallback. 

dpg.create_viewport(title=f"xAI Study Assistant - {agent.personality.name}", width=940, height=760)
dpg.setup_dearpygui()
dpg.show_viewport()
def exit_callback():
    dpg.stop_dearpygui()
    exit()
dpg.set_exit_callback(exit_callback)
dpg.start_dearpygui()
dpg.destroy_context()