import os
import json
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Try to import GenAI client
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

class ChatActionType(str, Enum):
    REPLACE_CODE = "replace_code"
    CREATE_FILE = "create_file"
    NONE = "none"

class ChatSuggestion(BaseModel):
    action: ChatActionType = Field(description="The action to perform: replace_code to patch the active file, create_file to create a new file, none if no action needed.")
    file_path: Optional[str] = Field(default=None, description="The file path to apply the action to (e.g. name of the current file or a new file).")
    original_code: Optional[str] = Field(default=None, description="For replace_code: the EXACT lines of original code in the file to be replaced. Indentation and characters must match exactly.")
    replacement_code: Optional[str] = Field(default=None, description="For replace_code: the suggested replacement code block.")
    new_file_content: Optional[str] = Field(default=None, description="For create_file: the complete content of the new file.")
    explanation: Optional[str] = Field(default=None, description="Brief explanation of why this code change is suggested.")

class ChatResponse(BaseModel):
    response: str = Field(description="The markdown formatted response answering the user's question, explaining concepts, or describing code.")
    suggestion: Optional[ChatSuggestion] = Field(default=None, description="Optional agentic code suggestion if the user asked to fix, write, modify, or create code.")

class ChatAssistant:
    def __init__(self, model_name: str = "gemini-3.1-flash-lite"):
        self.model_name = model_name
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = None
        
        if GENAI_AVAILABLE and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini client in ChatAssistant: {e}")

    def generate_chat_response(
        self,
        message: str,
        chat_history: List[Dict[str, str]],
        file_path: Optional[str] = None,
        file_content: Optional[str] = None,
        workspace_files: Optional[List[str]] = None
    ) -> ChatResponse:
        """
        Generates a conversational and agentic response from Gemini based on user message and IDE context.
        """
        if not self.client:
            return ChatResponse(
                response="Error: Gemini API Client is not initialized. Please ensure VITE_SUPABASE_URL or GEMINI_API_KEY is configured.",
                suggestion=None
            )

        # Build context strings
        context_str = ""
        if file_path and file_content:
            context_str += f"\n=== Current Active File: {file_path} ===\n{file_content}\n==================================\n"
        
        if workspace_files:
            context_str += f"\n=== Workspace Files ===\n" + "\n".join(workspace_files) + "\n=======================\n"

        system_instruction = (
            "You are Apex AI, an advanced agentic programming assistant integrated directly into the DevSync Collaborative Cloud IDE.\n"
            "Your goal is to answer the user's questions, explain code, and assist with debugging, refactoring, and writing code.\n"
            "You have direct context of the active file and the project structure. Use it to provide highly relevant answers.\n"
            "If the user asks you to modify code, fix a bug, write a function, or create a file, you must explain your answer AND "
            "provide a structured suggestion in the 'suggestion' field.\n"
            "Format of suggestions:\n"
            "- If editing the active file, set action to 'replace_code'. Make sure 'original_code' matches the exact substring in the file "
            "including all whitespace and indentation, and 'replacement_code' contains the new drop-in code block.\n"
            "- If creating a new file, set action to 'create_file', set 'file_path' to the new file name/path, and set 'new_file_content' to the full content.\n"
            "- Otherwise, set action to 'none'.\n"
            "Maintain a helpful, concise, and professional tone. Use markdown formatting in your response."
        )

        # Construct conversation history prompt
        history_str = ""
        for msg in chat_history:
            role_label = "Developer" if msg.get("role") == "user" else "Apex AI"
            history_str += f"{role_label}: {msg.get('content')}\n"

        prompt = f"""
{context_str}

=== Conversation History ===
{history_str}
Developer: {message}
Apex AI:
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ChatResponse,
                    system_instruction=system_instruction,
                    temperature=0.3,
                )
            )
            
            data = json.loads(response.text)
            return ChatResponse.model_validate(data)
        except Exception as e:
            print(f"Error during ChatAssistant LLM run: {e}")
            return ChatResponse(
                response=f"Error generating response: {str(e)}",
                suggestion=None
            )
