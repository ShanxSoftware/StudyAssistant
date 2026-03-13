from study_assistant.ui.console import main as console_main
from study_assistant.ui.gui import main as gui_main
from xaihandler import xAI_Handler
from xaihandler.personality import AgentPersonality, Archetype, AgentTrait, Trait
from xaihandler.memorystore import MemoryStore
from xaihandler.definitions import AutonomousOutput, JOB_STATUS, JobCard, BatchStatus

# from study_assistant.ui.gui import main as gui_main
try:
    from study_assistant.config import XAI_API_KEY, XAI_API_MODEL, XAI_TIMEOUT
except ValueError as e:
    print(e)
    exit(1)

def smoke_test(): 
    timeout: int = 3600 # Default if not set in .env or a bad value in .env
    try: 
        timeout = int(XAI_TIMEOUT)
    except Exception as e: 
        pass # TODO: Add a logger for tracking exceptions and errors
    agent = xAI_Handler(api_key=XAI_API_KEY, model=XAI_API_MODEL, timeout=timeout, validate_connection=False)
    agent.set_personality(
        AgentPersonality(
            name="Bob", 
            gender="male", 
            primary_archetype=Archetype.ANALYTICAL, 
            primary_weight=0.7, 
            secondary_archetype=Archetype.AMIABLE,
            secondary_weight=0.3,
            job_description="As a research and study assistant, your roles include maintaining the library of research articles, sumarising, collating, and synthising information, and finding new sources. Additionally, you help plan and proof assignments and provide exam preperation support.",
            traits=[AgentTrait(trait=Trait.PRECISION, intensity=70), AgentTrait(trait=Trait.CURIOSITY, intensity=30)]))
    
    response = agent.chat(message="Hi Bob, what's your job description?")
    print(response["content"])
    

if __name__ == "__main__":
    gui_main()
    #console_main()  # switch to gui_main() once ready
    #smoke_test()