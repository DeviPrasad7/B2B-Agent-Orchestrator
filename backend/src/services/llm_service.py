from langchain_core.messages import SystemMessage, HumanMessage
from core.logging import logger

from core.settings import settings


def _build_chat_models():
    """Instantiate the chat models for the configured provider.
    Returns a tuple of (gemini_pool, groq_pool)
    """
    
    gemini_keys = []
    if getattr(settings, "LLM_API_KEY", None):
        gemini_keys.append(settings.LLM_API_KEY)
    if getattr(settings, "LLM_API_KEY_2", None):
        gemini_keys.append(settings.LLM_API_KEY_2)
    if getattr(settings, "LLM_API_KEY_3", None):
        gemini_keys.append(settings.LLM_API_KEY_3)
    if getattr(settings, "LLM_API_KEY_4", None):
        gemini_keys.append(settings.LLM_API_KEY_4)
    if getattr(settings, "LLM_API_KEY_5", None):
        gemini_keys.append(settings.LLM_API_KEY_5)
        
    groq_keys = []
    if getattr(settings, "GROQ_API_KEYS", None):
        groq_keys = [k.strip() for k in settings.GROQ_API_KEYS.split(",") if k.strip()]
        
    groq_models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b"
    ]
    if getattr(settings, "GROQ_MODELS", None):
        groq_models = [m.strip() for m in settings.GROQ_MODELS.split(",") if m.strip()]

    gemini_models = [
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-2.5-flash"
    ]
    
    gemini_pool = []
    if gemini_keys:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            for key in gemini_keys:
                for m in gemini_models:
                    gemini_pool.append(ChatGoogleGenerativeAI(model=m, temperature=0.0, google_api_key=key))
        except ImportError:
            pass
            
    groq_pool = []
    if groq_keys:
        try:
            from langchain_groq import ChatGroq
            for key in groq_keys:
                for m in groq_models:
                    groq_pool.append(ChatGroq(model=m, temperature=0.0, groq_api_key=key))
        except ImportError:
            pass

    return gemini_pool, groq_pool


class LLMService:
    _global_lock = None
    _global_last_call_time = 0.0

    def __init__(self):
        self._gemini_pool = []
        self._groq_pool = []
        self._gemini_idx = 0
        self._groq_idx = 0
        self._initialized = False
        
        # Initialize the lock on the first instantiation (needs to be inside an event loop)
        import asyncio
        if LLMService._global_lock is None:
            try:
                LLMService._global_lock = asyncio.Lock()
            except RuntimeError:
                pass # Event loop might not be running yet
        
    def _ensure_initialized(self):
        if not self._initialized:
            self._gemini_pool, self._groq_pool = _build_chat_models()
            self._initialized = True

    def get_next_llm(self, strategy: str = "heavy"):
        self._ensure_initialized()
        
        # Always prioritize Groq due to higher rate limits
        if self._groq_pool:
            llm = self._groq_pool[self._groq_idx]
            self._groq_idx = (self._groq_idx + 1) % len(self._groq_pool)
            return llm
        elif self._gemini_pool:
            llm = self._gemini_pool[self._gemini_idx]
            self._gemini_idx = (self._gemini_idx + 1) % len(self._gemini_pool)
            return llm

        raise ValueError("No LLM clients available in the pools. Please configure API keys.")

    async def generate_text(self, prompt: str, fallback: str, require_json: bool = False, strategy: str = "heavy") -> str:
        self._ensure_initialized()
        
        # Groq has strict context limits (~6k tokens), so we truncate the raw character prompt to ~20000 chars safely.
        max_chars = 20000
        if len(prompt) > max_chars:
            prompt = prompt[:max_chars] + "\n...[TRUNCATED]"
            
        sys_msg = "You are a prospect summarizer AI."
        if require_json:
            sys_msg += " You must return ONLY valid JSON. Do not include markdown formatting or extra text."
        messages = [SystemMessage(content=sys_msg), HumanMessage(content=prompt)]
        
        # Always try Groq first, then Gemini
        pools = [self._groq_pool, self._gemini_pool]
            
        last_error = None
        for pool in pools:
            if not pool:
                continue
            
            # Try each model in the current pool exactly once
            for _ in range(len(pool)):
                llm = pool.pop(0)
                pool.append(llm) # Rotate to end for round-robin
                
                try:
                    import asyncio
                    import time
                    
                    # Ensure lock exists if it failed in __init__ due to no loop
                    if LLMService._global_lock is None:
                        LLMService._global_lock = asyncio.Lock()
                        
                    async with LLMService._global_lock:
                        now = time.time()
                        elapsed = now - LLMService._global_last_call_time
                        if elapsed < 2.5:
                            await asyncio.sleep(2.5 - elapsed)
                        LLMService._global_last_call_time = time.time()

                    if require_json:
                        response = await llm.bind(response_format={"type": "json_object"}).ainvoke(messages)
                    else:
                        response = await llm.ainvoke(messages)
                        
                    content = response.content
                    if isinstance(content, list):
                        content = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
                    return content
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"LLM generation failed for {llm.__class__.__name__}, retrying next...", error=last_error, strategy=strategy)
                    continue
                    
        logger.error("All LLM models in the pool failed.", last_error=last_error, strategy=strategy)
        return fallback
