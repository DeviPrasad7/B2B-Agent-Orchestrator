import time
from typing import Any
from langgraph.types import interrupt
from agent.state import GraphState, ValidationNote
from agent.utils import Toolbox, CircuitBreakerState, MonitoringService, MemoryStore

toolbox = Toolbox()
memory_store = MemoryStore()

async def monitor_node(state: GraphState) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    try:
        cb_state = toolbox.circuit_breaker.check_health("RSS_SOURCE")
        if cb_state == CircuitBreakerState.OPEN:
            MonitoringService.log_warning(prospect_id, "RSS source unavailable, skipping")
            return {"executed_agents": ["monitor_node"]}
            
        # We simulate reading an external feed for triggers
        website_url = state.get("data", {}).get("website_url")
        if website_url:
            page = await toolbox.fetch_webpage(website_url, 10)
        
        event_hash = f"event_{prospect_id}"
        memory_store.mark_event_processed(event_hash, prospect_id)
        toolbox.circuit_breaker.record_success("RSS_SOURCE")
        
        return {
            "executed_agents": ["monitor_node"],
            "data": {"raw_signals": [{"source": "RSS", "timestamp": time.time(), "content": "Trigger event detected"}]}
        }
    except Exception as e:
        toolbox.circuit_breaker.record_failure("RSS_SOURCE")
        MonitoringService.log_error(prospect_id, f"MONITOR_ERROR: {str(e)}")
        return {"executed_agents": ["monitor_node"], "errors": [f"monitor_node: {str(e)}"]}

async def score_node(state: GraphState) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    try:
        signals = state.get("data", {}).get("raw_signals", [])
        
        # Keyword matching scoring
        scored = [{"signal": s, "score": 85.0} for s in signals][:20]
        
        if not scored:
            MonitoringService.log_info(prospect_id, "No signals passed filter")
            return {
                "executed_agents": ["score_node"],
                "overall_status": "NO_ACTION"
            }
        
        return {
            "executed_agents": ["score_node"],
            "data": {"scored_signals": scored},
            "confidence_score": 50.0
        }
    except Exception as e:
        MonitoringService.log_error(prospect_id, f"SCORE_ERROR: {str(e)}")
        return {"executed_agents": ["score_node"], "errors": [f"score_node: {str(e)}"], "data": {"scored_signals": []}}

async def tech_stack_detector_node(state: GraphState) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    website_url = state.get("data", {}).get("website_url")
    if not website_url:
        return {"executed_agents": ["tech_stack_detector_node"]}

    try:
        cb_state = toolbox.circuit_breaker.check_health("TECH_DETECTION_API")
        if cb_state == CircuitBreakerState.OPEN:
            return {"executed_agents": ["tech_stack_detector_node"]}
            
        page = await toolbox.fetch_webpage(website_url, 10)
        stack = toolbox.detect_tech_stack(page.htmlContent, website_url)
        
        toolbox.circuit_breaker.record_success("TECH_DETECTION_API")
        return {
            "executed_agents": ["tech_stack_detector_node"],
            "data": {
                "tech_stack": [t.dict() for t in stack],
                "tech_source_map": {t.technology: t.source for t in stack}
            },
            "tech_detection_status": "SUCCESS"
        }
    except Exception as e:
        toolbox.circuit_breaker.record_failure("TECH_DETECTION_API")
        MonitoringService.log_warning(prospect_id, f"Website unreachable, partial data: {str(e)}")
        return {
            "executed_agents": ["tech_stack_detector_node"],
            "tech_detection_status": "PARTIAL",
            "validation_notes": [ValidationNote(level="WARN", message="Tech stack detection failed", source_agent="tech_stack", timestamp=time.time())],
            "errors": [f"tech_stack_detector_node: {str(e)}"]
        }

async def enricher_node(state: GraphState) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    company_name = state.get("data", {}).get("company_name", prospect_id)
    try:
        cb_state = toolbox.circuit_breaker.check_health("CRUNCHBASE_API")
        
        firmographics = {}
        data_sources = {}
        
        if cb_state != CircuitBreakerState.OPEN:
            cb_data = await toolbox.fetch_crunchbase(company_name)
            firmographics["name"] = cb_data.name
            firmographics["employeeCount"] = cb_data.employeeCount
            firmographics["revenue"] = cb_data.revenue
            firmographics["industries"] = cb_data.industries
            data_sources["crunchbase"] = "success"
            toolbox.circuit_breaker.record_success("CRUNCHBASE_API")
            
        li_data = await toolbox.scrape_linkedin(company_name)
        firmographics["location"] = li_data.get("location")
        data_sources["linkedin"] = "success"
        
        return {
            "executed_agents": ["enricher_node"],
            "data": {
                "firmographics": firmographics,
                "data_sources": data_sources
            }
        }
    except Exception as e:
        toolbox.circuit_breaker.record_failure("CRUNCHBASE_API")
        return {"executed_agents": ["enricher_node"], "errors": [f"enricher_node: {str(e)}"], "data": {"firmographics": {}}}

async def competitor_intel_node(state: GraphState) -> dict[str, Any]:
    tech_stack = state.get("data", {}).get("tech_stack", [])
    intel = {}
    for tech in tech_stack:
        name = tech.get("technology")
        comp_mapping = toolbox.get_competitor_info(name)
        if comp_mapping:
            intel[name] = comp_mapping.dict()
            
    if intel:
        return {
            "executed_agents": ["competitor_intel_node"],
            "data": {"competitor_intel": intel}
        }
    return {"executed_agents": ["competitor_intel_node"]} 

async def cross_validator_node(state: GraphState) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    firmographics = state.get("data", {}).get("firmographics", {})
    
    has_conflict = False
    notes = []
    
    # In memory cross-validation logic
    if not firmographics.get("name") or not firmographics.get("employeeCount"):
        notes.append(ValidationNote(
            level="WARN",
            message="Missing key firmographics (name or employeeCount)",
            source_agent="cross_validator",
            timestamp=time.time()
        ))
        
    confidence = 0.70 if notes else 0.95
    if notes:
        has_conflict = True
        MonitoringService.log_warning(prospect_id, "Validation issues found")
    
    return {
        "executed_agents": ["cross_validator_node"],
        "confidence_score": confidence,
        "has_conflict": has_conflict,
        "validation_notes": notes
    }

async def persona_matcher_node(state: GraphState) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    company_name = state.get("data", {}).get("company_name")
    
    if not company_name:
        return {"executed_agents": ["persona_matcher_node"]}
        
    try:
        from models.database import async_session
        from services.config_service import ConfigService
        async with async_session() as session:
            config_service = ConfigService(session)
            persona_def = await config_service.get_persona()
            
        employees = await toolbox.find_company_employees(company_name)
        
        # Simple mock filtering logic based on persona titles
        target_titles = [t.lower() for t in persona_def.job_titles]
        matched = []
        for emp in employees:
            emp_title = emp.get("title", "").lower()
            if any(t in emp_title for t in target_titles):
                matched.append({
                    "name": emp.get("name"),
                    "title": emp.get("title"),
                    "linkedin_url": emp.get("linkedin_url"),
                    "confidence": 0.9
                })
                
        return {
            "executed_agents": ["persona_matcher_node"],
            "data": {"personas": matched[:3]}
        }
    except Exception as e:
        MonitoringService.log_error(prospect_id, f"PERSONA_ERROR: {str(e)}")
        return {"executed_agents": ["persona_matcher_node"], "errors": [f"persona_matcher_node: {str(e)}"]}

async def contact_finder_node(state: GraphState) -> dict[str, Any]:
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

async def summarizer_node(state: GraphState) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    try:
        cb_state = toolbox.circuit_breaker.check_health("LLM_API")
        fallback_summary = '{"overview": "Fallback", "strengths": "Unknown", "risks": "Unknown", "recommendation": "Review manually"}'
        if cb_state == CircuitBreakerState.OPEN:
            MonitoringService.log_warning(prospect_id, "LLM circuit open, using fallback")
            return {
                "executed_agents": ["summarizer_node"],
                "data": {"summary_object": fallback_summary}
            }
        
        firmographics = state.get("data", {}).get("firmographics", {})
        prompt = f"Summarize this prospect: {firmographics}. Output JSON."
        summary = await toolbox.generate_text(prompt, fallback_summary)
        
        if summary == fallback_summary:
            toolbox.circuit_breaker.record_failure("LLM_API")
            MonitoringService.log_error(prospect_id, "LLM unavailable, using fallback")
        else:
            toolbox.circuit_breaker.record_success("LLM_API")
            
        return {
            "executed_agents": ["summarizer_node"],
            "data": {"summary_object": summary}
        }
    except Exception as e:
        toolbox.circuit_breaker.record_failure("LLM_API")
        return {
            "executed_agents": ["summarizer_node"],
            "data": {"summary_object": '{"overview": "Fallback", "strengths": "Unknown", "risks": "Unknown", "recommendation": "Review manually"}'},
            "errors": [f"summarizer_node: {str(e)}"]
        }

async def hitl_gateway_node(state: GraphState) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    confidence = state.get("confidence_score", 100.0)
    conflict = state.get("has_conflict", False)
    website = state.get("data", {}).get("website_url")
    
    needs_hitl = False
    hitl_reason = ""
    
    if not website:
        needs_hitl = True
        hitl_reason = "Missing website_url"
    elif confidence < 0.40 or conflict:
        needs_hitl = True
        hitl_reason = "Low confidence or data conflict"
    else:
        # Also always pause for final review if we made it to the end
        if state.get("data", {}).get("summary_object"):
            needs_hitl = True
            hitl_reason = "Final manual review requested"
            
    updates = {"executed_agents": ["hitl_gateway_node"]}
    
    if needs_hitl:
        toolbox.emit_event("HITL_REQUEST", {"prospect_id": prospect_id, "reason": hitl_reason})
        # Pause execution using LangGraph's inline interrupt
        # The user will resume with Command(resume={"action": "APPROVED", ...})
        response = interrupt({"prospect_id": prospect_id, "reason": hitl_reason, "state_snapshot": state})
        
        if response:
            action = response.get("action")
            if action in ["APPROVED", "EDITED"]:
                updates["overall_status"] = "APPROVED" if action == "APPROVED" else "EDITED"
            elif action == "REJECTED":
                updates["overall_status"] = "REJECTED"
            elif action == "TIMEOUT":
                updates["overall_status"] = "TIMEOUT"
            
            # Apply any edits to data
            if "edits" in response:
                updates["data"] = response["edits"]
                
            updates["human_override_payload"] = str(response)
            updates["validation_notes"] = [ValidationNote(level="INFO", message=f"Human intervention: {action}", source_agent="hitl", timestamp=time.time())]

    return updates

async def output_dispatcher_node(state: GraphState) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    try:
        export_record = {"prospect_id": prospect_id, "summary": state.get("data", {}).get("summary_object"), "status": state.get("overall_status")}
        
        event_hash = f"output_{prospect_id}"
        memory_store.mark_event_processed(event_hash, prospect_id)
        memory_store.save_prospect_state(prospect_id, state)
        
        toolbox.emit_event("PROSPECT_COMPLETED", export_record)
        toolbox.send_webhook("http://example.com/webhook", export_record)
        
        MonitoringService.log_success(prospect_id, "Execution completed successfully.")
        return {
            "executed_agents": ["output_dispatcher_node"]
        }
    except Exception as e:
        MonitoringService.log_error(prospect_id, "OUTPUT_FAILED")
        memory_store.rollback_prospect_state(prospect_id)
        return {"executed_agents": ["output_dispatcher_node"], "overall_status": "FAILED", "errors": [f"output_dispatcher_node: {str(e)}"]}

async def consolidation_node(state: GraphState) -> dict[str, Any]:
    """Node used strictly to converge parallel flows."""
    return {}
