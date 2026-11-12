import os
import json
import logging
import requests
from datetime import datetime
from typing import Generator, List, Dict, Any
from dotenv import load_dotenv

# Ensure .env is loaded before anything else
load_dotenv()

try:
    from google import genai
    from google.genai import types
    HAS_GOOGLE_GENAI = True
except ImportError:
    HAS_GOOGLE_GENAI = False

logger = logging.getLogger(__name__)


class AIService:
    """
    Production-grade Large Language Model (LLM) Integration Service.
    Uses official Google Gen AI Python SDK (google-genai) with multi-turn conversation memory.
    Supports Google Gemini (default), OpenAI, and Groq.
    """

    def __init__(self, config=None):
        # Refresh environment variables
        load_dotenv()

        if config:
            self.provider = getattr(config, 'AI_PROVIDER', os.getenv('AI_PROVIDER', 'gemini')).lower()
            self.gemini_key = (config.GEMINI_API_KEY if hasattr(config, 'GEMINI_API_KEY') else os.getenv('GEMINI_API_KEY', '')).strip()
            self.gemini_model = (config.GEMINI_MODEL if hasattr(config, 'GEMINI_MODEL') else os.getenv('GEMINI_MODEL', 'gemini-3.5-flash')).strip()
            self.openai_key = (config.OPENAI_API_KEY if hasattr(config, 'OPENAI_API_KEY') else os.getenv('OPENAI_API_KEY', '')).strip()
            self.openai_model = (config.OPENAI_MODEL if hasattr(config, 'OPENAI_MODEL') else os.getenv('OPENAI_MODEL', 'gpt-4o-mini')).strip()
            self.groq_key = (config.GROQ_API_KEY if hasattr(config, 'GROQ_API_KEY') else os.getenv('GROQ_API_KEY', '')).strip()
            self.groq_model = (config.GROQ_MODEL if hasattr(config, 'GROQ_MODEL') else os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')).strip()
            self.base_system_prompt = getattr(config, 'AI_SYSTEM_PROMPT', os.getenv('AI_SYSTEM_PROMPT', ''))
        else:
            self.provider = os.getenv('AI_PROVIDER', 'gemini').lower()
            self.gemini_key = os.getenv('GEMINI_API_KEY', '').strip()
            self.gemini_model = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash').strip()
            self.openai_key = os.getenv('OPENAI_API_KEY', '').strip()
            self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini').strip()
            self.groq_key = os.getenv('GROQ_API_KEY', '').strip()
            self.groq_model = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile').strip()
            self.base_system_prompt = os.getenv('AI_SYSTEM_PROMPT', '')

    def get_system_prompt(self) -> str:
        """Build dynamic system prompt with real-time date and context awareness."""
        now = datetime.now()
        date_context = (
            f"\n\nContext Information:"
            f"\n- Today's date is: {now.strftime('%A, %B %d, %Y')}."
            f"\n- Current local time is: {now.strftime('%I:%M %p')}."
        )
        return f"{self.base_system_prompt}{date_context}"

    def get_active_provider_info(self) -> Dict[str, Any]:
        """Return information about the currently active AI provider and model (never returning keys)."""
        if self.provider == 'gemini':
            return {
                'provider': 'gemini',
                'model': self.gemini_model or 'gemini-3.5-flash',
                'has_key': bool(self.gemini_key),
                'display_name': f"Google Gemini ({self.gemini_model or 'gemini-3.5-flash'})"
            }
        elif self.provider == 'openai':
            return {
                'provider': 'openai',
                'model': self.openai_model or 'gpt-4o-mini',
                'has_key': bool(self.openai_key),
                'display_name': f"OpenAI ({self.openai_model or 'gpt-4o-mini'})"
            }
        elif self.provider == 'groq':
            return {
                'provider': 'groq',
                'model': self.groq_model or 'llama-3.3-70b-versatile',
                'has_key': bool(self.groq_key),
                'display_name': f"Groq Cloud ({self.groq_model or 'llama-3.3-70b'})"
            }
        else:
            return {
                'provider': 'gemini',
                'model': self.gemini_model or 'gemini-3.5-flash',
                'has_key': bool(self.gemini_key),
                'display_name': f"Google Gemini ({self.gemini_model or 'gemini-3.5-flash'})"
            }

    def generate_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate a complete AI response using the configured real LLM provider."""
        provider = self.provider

        if provider == 'gemini':
            return self._call_gemini(messages)
        elif provider == 'openai':
            return self._call_openai(messages)
        elif provider == 'groq':
            return self._call_groq(messages)
        else:
            return self._call_gemini(messages)

    def stream_response(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """Stream tokens directly from the real LLM provider using Server-Sent Events."""
        provider = self.provider

        if provider == 'gemini':
            yield from self._stream_gemini(messages)
        elif provider == 'openai':
            yield from self._stream_openai(messages)
        elif provider == 'groq':
            yield from self._stream_groq(messages)
        else:
            yield from self._stream_gemini(messages)

    # --------------------------------------------------------------------------
    # 1. Google Gemini API via official google-genai SDK
    # --------------------------------------------------------------------------

    def _format_gemini_contents_genai(self, messages: List[Dict[str, str]]) -> List[Any]:
        """
        Format message history into google.genai types.Content objects.
        Merges consecutive messages of the same role and ensures first role is 'user'.
        """
        if not HAS_GOOGLE_GENAI:
            return []

        contents = []
        last_role = None

        for msg in messages:
            raw_role = msg.get("role", "user")
            role = "user" if raw_role == "user" else "model"
            text = (msg.get("content") or "").strip()

            if not text:
                continue

            # Gemini requires the first turn to be 'user'
            if not contents and role != "user":
                continue

            if role == last_role:
                # Merge consecutive turns of same role
                existing = contents[-1].parts
                if existing and hasattr(existing[0], 'text'):
                    existing[0].text += f"\n\n{text}"
            else:
                contents.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=text)])
                )
                last_role = role

        return contents

    def _call_gemini(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Call Google Gemini using the official google-genai SDK."""
        if not self.gemini_key:
            return {
                "content": (
                    "⚠️ **Google Gemini API Key is Not Configured**\n\n"
                    "NovaAI is set to use Google Gemini, but no API key was found in `.env`.\n\n"
                    "**How to configure:**\n"
                    "1. Open the `.env` file in the project directory.\n"
                    "2. Add your key: `GEMINI_API_KEY=your_actual_api_key_here`\n"
                    "3. Save the file and send your message again!"
                ),
                "provider": "gemini",
                "model": self.gemini_model,
                "is_error": True
            }

        if not HAS_GOOGLE_GENAI:
            return {
                "content": "⚠️ `google-genai` SDK is not installed. Please run `pip install google-genai`.",
                "provider": "gemini",
                "model": self.gemini_model,
                "is_error": True
            }

        try:
            client = genai.Client(api_key=self.gemini_key)
            contents = self._format_gemini_contents_genai(messages)

            if not contents:
                return {"content": "Please enter a message.", "provider": "gemini", "model": self.gemini_model}

            config = types.GenerateContentConfig(
                system_instruction=self.get_system_prompt(),
                temperature=0.7,
                max_output_tokens=4096
            )

            res = client.models.generate_content(
                model=self.gemini_model,
                contents=contents,
                config=config
            )

            text = res.text or ""
            return {
                "content": text.strip(),
                "provider": "gemini",
                "model": self.gemini_model,
                "is_error": False
            }

        except Exception as e:
            err_msg = str(e)
            if self.gemini_key and self.gemini_key in err_msg:
                err_msg = err_msg.replace(self.gemini_key, "[REDACTED_API_KEY]")
            logger.error(f"Gemini API error: {err_msg}")
            return {
                "content": f"⚠️ **Google Gemini API Error**: {err_msg}",
                "provider": "gemini",
                "model": self.gemini_model,
                "is_error": True
            }

    def _stream_gemini(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """Stream response chunks from Google Gemini API via official google-genai SDK."""
        if not self.gemini_key:
            error_notice = (
                "⚠️ **Google Gemini API Key is Not Configured**\n\n"
                "Please add `GEMINI_API_KEY=your_key` in `.env` to enable real AI generation.\n"
                "Get a free key at [Google AI Studio](https://aistudio.google.com/app/apikey)."
            )
            yield json.dumps({"delta": error_notice, "provider": "gemini", "is_error": True}) + "\n"
            yield json.dumps({"done": True, "provider": "gemini", "full_content": error_notice}) + "\n"
            return

        if not HAS_GOOGLE_GENAI:
            error_notice = "⚠️ `google-genai` SDK is not installed. Please run `pip install google-genai`."
            yield json.dumps({"delta": error_notice, "provider": "gemini", "is_error": True}) + "\n"
            yield json.dumps({"done": True, "provider": "gemini", "full_content": error_notice}) + "\n"
            return

        try:
            client = genai.Client(api_key=self.gemini_key)
            contents = self._format_gemini_contents_genai(messages)

            if not contents:
                yield json.dumps({"delta": "Please enter a message."}) + "\n"
                yield json.dumps({"done": True}) + "\n"
                return

            config = types.GenerateContentConfig(
                system_instruction=self.get_system_prompt(),
                temperature=0.7,
                max_output_tokens=4096
            )

            response_stream = client.models.generate_content_stream(
                model=self.gemini_model,
                contents=contents,
                config=config
            )

            full_text = []
            for chunk in response_stream:
                if chunk.text:
                    full_text.append(chunk.text)
                    yield json.dumps({"delta": chunk.text, "provider": "gemini"}) + "\n"

            yield json.dumps({
                "done": True,
                "provider": "gemini",
                "model": self.gemini_model,
                "full_content": "".join(full_text)
            }) + "\n"

        except Exception as e:
            err_msg = str(e)
            if self.gemini_key and self.gemini_key in err_msg:
                err_msg = err_msg.replace(self.gemini_key, "[REDACTED_API_KEY]")
            logger.error(f"Gemini stream error: {err_msg}")
            yield json.dumps({
                "delta": f"⚠️ **Google Gemini Stream Error**: {err_msg}",
                "provider": "gemini",
                "is_error": True
            }) + "\n"
            yield json.dumps({"done": True, "provider": "gemini"}) + "\n"

    # --------------------------------------------------------------------------
    # 2. OpenAI API Implementation
    # --------------------------------------------------------------------------

    def _call_openai(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Call OpenAI Chat Completions API."""
        if not self.openai_key:
            return {
                "content": (
                    "⚠️ **OpenAI API Key is Not Configured**\n\n"
                    "Please add `OPENAI_API_KEY=your_key` in `.env` to use OpenAI models."
                ),
                "provider": "openai",
                "model": self.openai_model,
                "is_error": True
            }

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }

        payload_messages = [{"role": "system", "content": self.get_system_prompt()}]
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                payload_messages.append({"role": role, "content": content})

        payload = {
            "model": self.openai_model,
            "messages": payload_messages,
            "temperature": 0.7
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code != 200:
                err_text = resp.json().get("error", {}).get("message", resp.text)
                return {
                    "content": f"⚠️ **OpenAI Error** ({resp.status_code}): {err_text}",
                    "provider": "openai",
                    "model": self.openai_model,
                    "is_error": True
                }

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return {
                "content": content,
                "provider": "openai",
                "model": self.openai_model,
                "is_error": False
            }
        except Exception as e:
            return {
                "content": f"⚠️ **OpenAI Connection Error**: {str(e)}",
                "provider": "openai",
                "model": self.openai_model,
                "is_error": True
            }

    def _stream_openai(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """Stream chunks from OpenAI API."""
        if not self.openai_key:
            error_notice = "⚠️ **OpenAI API Key is Not Configured**. Please add `OPENAI_API_KEY` in `.env`."
            yield json.dumps({"delta": error_notice, "provider": "openai", "is_error": True}) + "\n"
            yield json.dumps({"done": True, "provider": "openai", "full_content": error_notice}) + "\n"
            return

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        payload_messages = [{"role": "system", "content": self.get_system_prompt()}]
        for msg in messages:
            content = msg.get("content", "")
            if content:
                payload_messages.append({"role": msg.get("role", "user"), "content": content})

        payload = {
            "model": self.openai_model,
            "messages": payload_messages,
            "temperature": 0.7,
            "stream": True
        }

        full_text = []
        try:
            resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
            if resp.status_code != 200:
                yield json.dumps({"delta": f"⚠️ **OpenAI Error** ({resp.status_code}): {resp.text}", "is_error": True}) + "\n"
                yield json.dumps({"done": True}) + "\n"
                return

            for line in resp.iter_lines():
                if not line:
                    continue
                line_str = line.decode('utf-8')
                if line_str.startswith("data: "):
                    data_str = line_str[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk['choices'][0].get('delta', {}).get('content', '')
                        if delta:
                            full_text.append(delta)
                            yield json.dumps({"delta": delta, "provider": "openai"}) + "\n"
                    except Exception:
                        continue

            yield json.dumps({
                "done": True,
                "provider": "openai",
                "model": self.openai_model,
                "full_content": "".join(full_text)
            }) + "\n"
        except Exception as e:
            yield json.dumps({"delta": f"\n\n⚠️ **Stream Error**: {str(e)}", "is_error": True}) + "\n"
            yield json.dumps({"done": True}) + "\n"

    # --------------------------------------------------------------------------
    # 3. Groq API Implementation (Llama-3.3-70b)
    # --------------------------------------------------------------------------

    def _call_groq(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Call Groq API."""
        if not self.groq_key:
            return {
                "content": (
                    "⚠️ **Groq API Key is Not Configured**\n\n"
                    "Please add `GROQ_API_KEY=your_key` in `.env` to use Groq models."
                ),
                "provider": "groq",
                "model": self.groq_model,
                "is_error": True
            }

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }
        payload_messages = [{"role": "system", "content": self.get_system_prompt()}]
        for msg in messages:
            content = msg.get("content", "")
            if content:
                payload_messages.append({"role": msg.get("role", "user"), "content": content})

        payload = {
            "model": self.groq_model,
            "messages": payload_messages,
            "temperature": 0.7
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code != 200:
                err_text = resp.json().get("error", {}).get("message", resp.text)
                return {
                    "content": f"⚠️ **Groq Error** ({resp.status_code}): {err_text}",
                    "provider": "groq",
                    "model": self.groq_model,
                    "is_error": True
                }

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return {
                "content": content,
                "provider": "groq",
                "model": self.groq_model,
                "is_error": False
            }
        except Exception as e:
            return {
                "content": f"⚠️ **Groq Connection Error**: {str(e)}",
                "provider": "groq",
                "model": self.groq_model,
                "is_error": True
            }

    def _stream_groq(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """Stream chunks from Groq API."""
        if not self.groq_key:
            error_notice = "⚠️ **Groq API Key is Not Configured**. Please add `GROQ_API_KEY` in `.env`."
            yield json.dumps({"delta": error_notice, "provider": "groq", "is_error": True}) + "\n"
            yield json.dumps({"done": True, "provider": "groq", "full_content": error_notice}) + "\n"
            return

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }
        payload_messages = [{"role": "system", "content": self.get_system_prompt()}]
        for msg in messages:
            content = msg.get("content", "")
            if content:
                payload_messages.append({"role": msg.get("role", "user"), "content": content})

        payload = {
            "model": self.groq_model,
            "messages": payload_messages,
            "temperature": 0.7,
            "stream": True
        }

        full_text = []
        try:
            resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
            if resp.status_code != 200:
                yield json.dumps({"delta": f"⚠️ **Groq Error** ({resp.status_code}): {resp.text}", "is_error": True}) + "\n"
                yield json.dumps({"done": True}) + "\n"
                return

            for line in resp.iter_lines():
                if not line:
                    continue
                line_str = line.decode('utf-8')
                if line_str.startswith("data: "):
                    data_str = line_str[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk['choices'][0].get('delta', {}).get('content', '')
                        if delta:
                            full_text.append(delta)
                            yield json.dumps({"delta": delta, "provider": "groq"}) + "\n"
                    except Exception:
                        continue

            yield json.dumps({
                "done": True,
                "provider": "groq",
                "model": self.groq_model,
                "full_content": "".join(full_text)
            }) + "\n"
        except Exception as e:
            yield json.dumps({"delta": f"\n\n⚠️ **Stream Error**: {str(e)}", "is_error": True}) + "\n"
            yield json.dumps({"done": True}) + "\n"
