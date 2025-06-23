# agents/cognitive_agent.py

import os
import json
from openai import OpenAI

class CognitiveAgent:
    """
    An agent that uses a master prompt to extract structured data from text.
    """
    def __init__(self, prompt_path="prompts/V1_Cognitive_Agent_Prompt.txt"):
        """
        Initializes the agent and loads the master prompt from a file.
        """
        try:
            with open(prompt_path, "r") as f:
                self.master_prompt_template = f.read()
            # Initialize OpenAI client
            self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            print(f"CognitiveAgent initialized successfully from {prompt_path}")
        except FileNotFoundError:
            print(f"ERROR: Prompt file not found at {prompt_path}")
            self.master_prompt_template = "" # Ensure agent can still be created
            self.client = None
        except Exception as e:
            print(f"ERROR: Failed to initialize OpenAI client: {e}")
            self.client = None

    def extract_structured_data(self, ocr_text: str) -> dict | None:
        """
        Takes raw OCR text, uses OpenAI API to extract structured JSON data.
        """
        if not self.master_prompt_template:
            print("ERROR: Cannot extract data, master prompt is not loaded.")
            return None
            
        if not self.client:
            print("ERROR: OpenAI client not initialized.")
            return None

        try:
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": self.master_prompt_template
                    },
                    {
                        "role": "user", 
                        "content": f"Please extract structured data from this document text:\n\n{ocr_text}"
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            if content is None:
                print("ERROR: Empty response from OpenAI API")
                return None
                
            result = json.loads(content)
            print(f"Successfully extracted structured data using OpenAI API")
            return result
            
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse JSON response: {e}")
            return None
        except Exception as e:
            print(f"ERROR: OpenAI API call failed: {e}")
            return None