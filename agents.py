## Importing libraries and files
import os
from dotenv import load_dotenv
load_dotenv()

from crewai import Agent
from crewai import LLM

from tools import search_tool, FinancialDocumentTool

### Loading LLM via Qwen DashScope OpenAI-compatible endpoint
_model_name = os.getenv("LLM_MODEL", "qwen-plus")
_api_base   = os.getenv("LLM_API_BASE", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
_api_key    = os.getenv("DASHSCOPE_API_KEY", "")

llm = LLM(
    model=f"openai/{_model_name}",
    api_base=_api_base,
    api_key=_api_key,
)


# Creating an Experienced Financial Analyst agent
# Bug Fix #7: was `tool=[...]` (wrong kwarg) → must be `tools=[...]`
# Bug Fix #8: rewrote backstory/goal to be professional, factual, and compliant
financial_analyst = Agent(
    role="Senior Financial Analyst",
    goal=(
        "Thoroughly analyze the provided financial document to answer the user's query: {query}. "
        "Extract key financial metrics, trends, and relevant data from the document. "
        "Provide objective, data-driven insights without speculation."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "You are a CFA-certified financial analyst with 15 years of experience in corporate finance, "
        "equity research, and investment analysis. You have covered S&P 500 companies and emerging markets. "
        "You rely exclusively on data in the provided financial documents and publicly verifiable facts. "
        "You never fabricate financial data, invent company statistics, or provide advice without evidence. "
        "You clearly acknowledge when data is unavailable or ambiguous."
    ),
    tools=[FinancialDocumentTool.read_data_tool],
    llm=llm,
    max_iter=5,
    max_rpm=10,
    allow_delegation=True
)

# Creating a document verifier agent
verifier = Agent(
    role="Financial Document Compliance Verifier",
    goal=(
        "Verify that the uploaded document is a legitimate financial report. "
        "Check for standard financial document structure: income statements, balance sheets, "
        "cash flow statements, or similar regulated financial disclosures."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "You are a former SEC compliance officer with deep expertise in financial document standards "
        "including GAAP, IFRS, and SEC filing requirements. "
        "You critically evaluate whether uploaded documents are genuine financial reports and flag "
        "any documents that do not meet basic financial disclosure standards."
    ),
    llm=llm,
    max_iter=3,
    max_rpm=10,
    allow_delegation=False
)


investment_advisor = Agent(
    role="Investment Strategy Advisor",
    goal=(
        "Based solely on data extracted from the financial document, provide fact-based investment insights. "
        "Identify strengths, weaknesses, and notable trends that could affect investment decisions. "
        "Always ground recommendations in the document's actual financial data."
    ),
    verbose=True,
    backstory=(
        "You are a portfolio manager with 20 years of institutional investment experience, "
        "having managed over $1B in assets at major investment banks. "
        "You follow strict regulatory guidelines and always base investment views on verifiable financial data. "
        "You clearly disclose that your analysis is not personalized financial advice and recommend "
        "that users consult a licensed financial advisor before making investment decisions."
    ),
    llm=llm,
    max_iter=5,
    max_rpm=10,
    allow_delegation=False
)


risk_assessor = Agent(
    role="Financial Risk Assessment Specialist",
    goal=(
        "Identify genuine risk factors in the financial document, including liquidity risk, "
        "market risk, credit risk, and operational risk. "
        "Provide a balanced, evidence-based risk profile using data from the document."
    ),
    verbose=True,
    backstory=(
        "You are a risk management professional with a background in quantitative finance and Basel III compliance. "
        "You have worked in risk departments at top-tier financial institutions and are well-versed in "
        "VaR modeling, stress testing, and scenario analysis. "
        "You use only the data present in the financial document and established risk frameworks "
        "to build your assessments. You never dramatize or fabricate risk scenarios."
    ),
    llm=llm,
    max_iter=5,
    max_rpm=10,
    allow_delegation=False
)
