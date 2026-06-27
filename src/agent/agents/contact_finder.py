import time
from typing import Any
from ..state import GraphState
from ..utils import Toolbox
from services.memory_service import MemoryService, MonitoringService

async def contact_finder_node(
    state: GraphState,
    toolbox: Toolbox,
    memory: MemoryService,
) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    personas = state.get("data", {}).get("personas", [])
    website_url = state.get("data", {}).get("website_url", "")
    
    domain = website_url.replace("https://", "").replace("http://", "").split("/")[0] if website_url else "example.com"
    
    if not personas:
        return {"executed_agents": ["contact_finder_node"]}
        
    try:
        contacts = []
        for persona in personas:
            contact = await toolbox.enrich_contact(persona["name"], domain)
            contact["persona_name"] = persona["name"]
            contacts.append(contact)
            
        return {
            "executed_agents": ["contact_finder_node"],
            "data": {"contacts": contacts}
        }
    except Exception as e:
        MonitoringService.log_error(prospect_id, f"CONTACT_ERROR: {str(e)}")
        return {"executed_agents": ["contact_finder_node"], "errors": [f"contact_finder_node: {str(e)}"]}
