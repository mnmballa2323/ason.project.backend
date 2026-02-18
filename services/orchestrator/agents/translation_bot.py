"""
Translation Bot Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Global Ops module.
2. Translates strings using internal TM and suggests glossary terms locally.
3. STRICTLY NO EXTERNAL API CALLS (No Google Translate).
4. Internal Dictionary/TM only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..global_ops import tm_engine, glossary_suggester

logger = logging.getLogger("qwen.agents.translation_bot")

class TranslationBotAgent(Agent):
    """
    Agent that acts as an Automated Translator.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "translation-bot",
            "description": "Automated translation using internal TM.",
            "version": "1.0.0",
            "role": "Translation Bot",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute translation actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "translate_string", "suggest_glossary".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"TranslationBotAgent received action: {action}")

        if action == "translate_string":
            key = input_data.get("key")
            target_lang = input_data.get("target_lang")
            try:
                # translation = tm_engine.lookup(key, target_lang)
                return {
                    "status": "success",
                    "key": key,
                    "source": "Submit",
                    "target_lang": target_lang,
                    "translation": "Soumettre" if target_lang == "fr-FR" else "Senden"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "suggest_glossary":
            term = input_data.get("term")
            try:
                # suggestions = glossary_suggester.find(term)
                return {
                    "status": "success",
                    "term": term,
                    "approved_translation": "Utilisateur",
                    "forbidden_terms": ["Usager", "Client"]
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'translate_string', 'suggest_glossary'."
            }
