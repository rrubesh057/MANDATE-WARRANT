from __future__ import annotations
import json, os
class AIServiceError(RuntimeError): pass
def call_claude(system,user):
    key=os.getenv("ANTHROPIC_API_KEY")
    if not key: raise AIServiceError("ANTHROPIC_API_KEY is required. No simulated AI result was produced.")
    try:
        from anthropic import Anthropic
        response=Anthropic(api_key=key).messages.create(model=os.getenv("CLAUDE_MODEL","claude-3-5-haiku-latest"),max_tokens=800,system=system,messages=[{"role":"user","content":user}])
        return json.loads("".join(block.text for block in response.content if getattr(block,"type",None)=="text"))
    except Exception as error: raise AIServiceError(f"Claude request failed: {error}") from error
