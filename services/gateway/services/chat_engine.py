"""
Chat Engine Service
Routes natural language queries to internal agents.
STRICTLY INTERNAL USE ONLY.
"""

from typing import Dict, Any

class ChatEngine:
    async def process_message(self, user: str, message: str) -> Dict[str, Any]:
        """
        Simple intent matching to route to agents.
        """
        message_lower = message.lower()
        
        response = {
            "user": user,
            "original_message": message,
            "agent_response": "I didn't understand that request."
        }
        
        if "pay" in message_lower or "salary" in message_lower:
            response["agent_response"] = "[Payroll Agent] Your latest paystub is available in the localized secure vault."
        elif "password" in message_lower or "login" in message_lower:
            response["agent_response"] = "[IT Agent] Please use the IDM portal to reset your credentials."
        elif "policy" in message_lower or "compliance" in message_lower:
            response["agent_response"] = "[Policy Drafter] Our Zero-Trust policy is strictly enforced. Refer to Doc-99."
            
        return response

# Singleton
chat_service = ChatEngine()
