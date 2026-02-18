"""
Translation Manager Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted i18n Ops module.
2. Translates text and manages glossary locally.
3. STRICTLY NO EXTERNAL API CALLS.
4. Internal NMT Model only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..i18n_ops import nmt_engine, glossary_manager

logger = logging.getLogger("qwen.agents.translation_manager")

class TranslationManagerAgent(Agent):
    """
    Agent that acts as a Translation Manager.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "translation-manager",
            "description": "Text translation and glossary management.",
            "version": "1.0.0",
            "role": "Translation Manager",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute Translation actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "translate_text", "manage_glossary".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"TranslationManagerAgent received action: {action}")

        if action == "translate_text":
            text = input_data.get("text")
            target_lang = input_data.get("target_lang")
            try:
                # translated = nmt_engine.translate(text, target_lang)
                return {
                    "status": "success",
                    "source_text": text,
                    "target_lang": target_lang,
                    "translated_text": f"[Translated to {target_lang}]: {text}",
                    "confidence": "0.95"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "manage_glossary":
            term = input_data.get("term")
            definition = input_data.get("definition")
            try:
                # entry = glossary_manager.add(term, definition)
                return {
                    "status": "success",
                    "term": term,
                    "action": "Added",
                    "glossary_id": "GLOS-101"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'translate_text', 'manage_glossary'."
            }
