import litellm
from typing import Dict, Any
import backoff
import os

class LiteLLMFallback:
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def completion_with_fallback(self, prompt: str) -> Dict[str, Any]:
        try:
            response = litellm.completion(
                model=os.getenv("LITELLM_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt}]
            )
            return {"status": "success", "response": response.choices[0].message.content}
        except Exception as e:
            print(f"LLM error, attempting fallback: {str(e)}")
            try:
                response = litellm.completion(
                    model="claude-3.5-sonnet",
                    messages=[{"role": "user", "content": prompt}]
                )
                return {"status": "success", "response": response.choices[0].message.content}
            except Exception as fallback_e:
                print(f"Fallback failed: {str(fallback_e)}")
                return {"status": "error", "message": str(fallback_e)}
