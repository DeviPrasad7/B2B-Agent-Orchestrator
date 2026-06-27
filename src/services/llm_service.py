from langchain_core.messages import SystemMessage, HumanMessage
import structlog

from core.settings import settings

logger = structlog.get_logger()


def _build_chat_model():
    """Instantiate the chat model for the configured provider.

    Supported values for ``settings.LLM_PROVIDER``:
    - ``"openai"``  → requires ``langchain-openai``
    - ``"gemini"``  → requires ``langchain-google-genai``
    - ``"groq"``    → requires ``langchain-groq``
    """
    provider = settings.LLM_PROVIDER.lower()
    model = settings.LLM_MODEL
    api_key = settings.LLM_API_KEY

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, temperature=0.0, api_key=api_key)

    if provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError(
                "langchain-google-genai is required when LLM_PROVIDER='gemini'. "
                "Install it with: pip install langchain-google-genai"
            )
        return ChatGoogleGenerativeAI(model=model, temperature=0.0, google_api_key=api_key)

    if provider == "groq":
        try:
            from langchain_groq import ChatGroq
        except ImportError:
            raise ImportError(
                "langchain-groq is required when LLM_PROVIDER='groq'. "
                "Install it with: pip install langchain-groq"
            )
        return ChatGroq(model=model, temperature=0.0, groq_api_key=api_key)

    raise ValueError(
        f"Unsupported LLM_PROVIDER='{provider}'. "
        "Choose from: openai, gemini, groq"
    )


class LLMService:
    def __init__(self):
        self._llm = None
        
    @property
    def llm(self):
        if not self._llm:
            self._llm = _build_chat_model()
        return self._llm

    async def generate_text(self, prompt: str, fallback: str) -> str:
        try:
            messages = [SystemMessage(content="You are a prospect summarizer AI."), HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error("LLM generation failed", error=str(e))
            return fallback
