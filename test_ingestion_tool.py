import os
import logging
from langchain_tools import IngestionTool

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_ingestion_tool():
    """Tests the IngestionTool."""
    print("--- Testing IngestionTool ---")

    # Define a test file
    test_file_path = "test_ingestion_document.txt"

    try:
        # Create the dummy document
        with open(test_file_path, "w") as f:
            f.write("This is a test document for the LangChain IngestionTool.")
        print(f"Created test document at: {test_file_path}")

        # Initialize and run the tool
        ingestion_tool = IngestionTool()
        result = ingestion_tool.run(test_file_path)

        # Print the result
        print(f"\nTool Result: {result}")

        if "Successfully" in result:
            print("\n✅ Test Passed: IngestionTool ran successfully.")
        else:
            print("\n❌ Test Failed: IngestionTool encountered an error.")

    finally:
        # Clean up the test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            print(f"Cleaned up test file: {test_file_path}")

if __name__ == "__main__":
    test_ingestion_tool()