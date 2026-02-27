## Importing libraries and files
import os
import requests
from dotenv import load_dotenv
load_dotenv()

from crewai.tools import tool
from langchain_community.document_loaders import PyPDFLoader

## Creating search tool (native Serper implementation — no crewai_tools dependency)
@tool("Web Search")
def search_tool(query: str) -> str:
    """Search the web for real-time financial information using Serper.

    Args:
        query (str): Search query string.

    Returns:
        str: Top search results as formatted text.
    """
    api_key = os.getenv("SERPER_API_KEY", "")
    if not api_key:
        return "Web search unavailable: SERPER_API_KEY not set."
    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": 5},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        results = []
        for item in data.get("organic", [])[:5]:
            results.append(f"- {item.get('title', '')}: {item.get('snippet', '')} ({item.get('link', '')})")
        return "\n".join(results) if results else "No results found."
    except Exception as exc:
        return f"Search failed: {exc}"


## Creating custom pdf reader tool — module-level @tool function
@tool("Financial Document Reader")
def read_financial_document(path: str = 'data/sample.pdf') -> str:
    """Tool to read and extract text from a financial PDF document.

    Args:
        path (str): Path to the PDF file. Use the EXACT path provided in the task description.

    Returns:
        str: Full extracted text from the financial document.
    """
    # Resolve to absolute path in case a relative path is given
    if not os.path.isabs(path):
        # Try relative to the current working directory
        abs_path = os.path.abspath(path)
    else:
        abs_path = path

    if not os.path.exists(abs_path):
        return (
            f"ERROR: File not found at '{abs_path}'. "
            "Please use the EXACT file path provided in the task description. "
            "Do not guess or invent paths."
        )

    try:
        loader = PyPDFLoader(file_path=abs_path)
        docs = loader.load()

        full_report = ""
        for data in docs:
            content = data.page_content
            while "\n\n" in content:
                content = content.replace("\n\n", "\n")
            full_report += content + "\n"

        return full_report or "No content could be extracted from the document."
    except Exception as e:
        return f"Error reading PDF: {e}"


## Expose via a class for backward-compatible imports used in agents/tasks
class FinancialDocumentTool:
    read_data_tool = read_financial_document


## Creating Investment Analysis Tool
class InvestmentTool:
    @staticmethod
    def analyze_investment_tool(financial_document_data: str) -> str:
        """Process and analyze the financial document data."""
        processed_data = financial_document_data

        # Clean up the data format (remove double spaces)
        i = 0
        while i < len(processed_data):
            if processed_data[i:i+2] == "  ":  # Remove double spaces
                processed_data = processed_data[:i] + processed_data[i+1:]
            else:
                i += 1

        # TODO: Implement investment analysis logic here
        return "Investment analysis functionality to be implemented"


## Creating Risk Assessment Tool
class RiskTool:
    @staticmethod
    def create_risk_assessment_tool(financial_document_data: str) -> str:
        """Create a risk assessment from the financial document data."""
        # TODO: Implement risk assessment logic here
        return "Risk assessment functionality to be implemented"