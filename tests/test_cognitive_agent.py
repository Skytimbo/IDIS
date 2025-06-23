# tests/test_cognitive_agent.py

import unittest
import os
from agents.cognitive_agent import CognitiveAgent

class TestCognitiveAgent(unittest.TestCase):

    def test_agent_initialization(self):
        """
        Tests that the agent can be initialized and loads the prompt file.
        """
        # Note: This test assumes the prompt file exists at the specified path.
        # A more robust test suite might create a temporary prompt file.
        agent = CognitiveAgent(prompt_path="prompts/V1_Cognitive_Agent_Prompt.txt")
        self.assertIn("You are a highly precise, automated data extraction engine.", agent.master_prompt_template)
        print("\nTestCognitiveAgent: Initialization test passed.")

    def test_extract_data_method_exists(self):
        """
        Tests that the main data extraction method exists and returns a dict.
        """
        agent = CognitiveAgent(prompt_path="prompts/V1_Cognitive_Agent_Prompt.txt")
        sample_text = "This is a test."
        result = agent.extract_structured_data(sample_text)
        self.assertIsInstance(result, dict)
        print("TestCognitiveAgent: Method existence test passed.")

if __name__ == '__main__':
    # This allows running the tests directly from the command line
    unittest.main()