# ---- 5a.  helper that retries on transient OpenAI (5xx) errors ----------
import openai
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(                       # 2 s → 4 s → 8 s → 16 s (max 4 retries)
    wait=wait_exponential(multiplier=1, min=2, max=16),
    stop=stop_after_attempt(5),
    retry_error_callback=lambda retry_state: (_ for _ in ()).throw(retry_state.outcome.exception()),
)
def invoke_with_retry(executor, user_prompt: str):
    """Run the agent with back‑off on 5xx errors from Azure OpenAI."""
    return executor.invoke({"input": user_prompt})
