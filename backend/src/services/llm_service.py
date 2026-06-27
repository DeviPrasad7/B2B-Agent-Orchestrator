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
        "gemini-3-flash",
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
    def __init__(self):
        self._gemini_pool = []
        self._groq_pool = []
        self._gemini_idx = 0
        self._groq_idx = 0
        self._initialized = False
        
    def _ensure_initialized(self):
        if not self._initialized:
            self._gemini_pool, self._groq_pool = _build_chat_models()
            self._initialized = True

    def get_next_llm(self, strategy: str = "heavy"):
        self._ensure_initialized()
        
        # Heavy strategy -> use Gemini if available
        if strategy == "heavy":
            if self._gemini_pool:
                llm = self._gemini_pool[self._gemini_idx]
                self._gemini_idx = (self._gemini_idx + 1) % len(self._gemini_pool)
                return llm
            elif self._groq_pool:
                # Fallback to groq if no gemini
                llm = self._groq_pool[self._groq_idx]
                self._groq_idx = (self._groq_idx + 1) % len(self._groq_pool)
                return llm
                
        # Fast strategy -> use Groq if available
        if strategy == "fast":
            if self._groq_pool:
                llm = self._groq_pool[self._groq_idx]
                self._groq_idx = (self._groq_idx + 1) % len(self._groq_pool)
                return llm
            elif self._gemini_pool:
                # Fallback to gemini if no groq
                llm = self._gemini_pool[self._gemini_idx]
                self._gemini_idx = (self._gemini_idx + 1) % len(self._gemini_pool)
                return llm

        raise ValueError("No LLM clients available in the pools. Please configure API keys.")

    async def generate_text(self, prompt: str, fallback: str, require_json: bool = False, strategy: str = "heavy") -> str:
        try:
            sys_msg = "You are a prospect summarizer AI."
            if require_json:
                sys_msg += " You must return ONLY valid JSON. Do not include markdown formatting or extra text."
            messages = [SystemMessage(content=sys_msg), HumanMessage(content=prompt)]
            
            llm = self.get_next_llm(strategy=strategy)
            
            # Note: Groq also supports response_format for JSON mode
            if require_json:
                response = await llm.bind(response_format={"type": "json_object"}).ainvoke(messages)
            else:
                response = await llm.ainvoke(messages)
                
            return response.content
        except Exception as e:
            logger.error("LLM generation failed", error=str(e), strategy=strategy)
            return fallback
