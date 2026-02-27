## Importing libraries and files
from crewai import Task

# Bug Fix #10-12: import all dedicated agents (verifier, investment_advisor, risk_assessor)
from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from tools import search_tool, FinancialDocumentTool

## Creating a task to analyze the financial document
# Bug Fix #9 & #13: rewrote description/expected_output — removed hallucination-encouraging
#                   instructions, fake URLs, and contradictory advice prompts
analyze_financial_document = Task(
    description=(
        "Analyze the financial document located at the file path provided in the context. "
        "Use the Financial Document Reader tool to extract the full text from the document. "
        "Then answer the user's query: {query}\n\n"
        "Your analysis must:\n"
        "1. Summarize key financial metrics (revenue, profit, EPS, margins, cash flow, debt ratios, etc.)\n"
        "2. Identify notable year-over-year or quarter-over-quarter trend changes\n"
        "3. Highlight any management guidance or forward-looking statements in the document\n"
        "4. Directly and specifically answer the user's query using data from the document\n"
        "5. Note any data limitations or areas where the document does not provide enough information\n\n"
        "Do NOT invent, extrapolate, or fabricate any financial figures. "
        "Only use data that is explicitly stated in the document. "
        "The document file path is: {file_path}"
    ),
    expected_output=(
        "A structured financial analysis report containing:\n"
        "- **Executive Summary**: 2-3 sentence overview of the document and findings\n"
        "- **Key Financial Metrics**: Table or bullet list of the most important figures\n"
        "- **Trend Analysis**: Notable changes compared to previous periods (if available in document)\n"
        "- **Answer to Query**: Direct, specific answer to '{query}' with supporting data\n"
        "- **Data Limitations**: Any gaps or caveats noted from the document\n\n"
        "All figures must be sourced directly from the document. "
        "Do not include URLs, external links, or information not present in the document."
    ),
    agent=financial_analyst,
    tools=[FinancialDocumentTool.read_data_tool],
    async_execution=False,
)

## Creating an investment analysis task
# Bug Fix #11: was `agent=financial_analyst` → correct agent is `investment_advisor`
investment_analysis = Task(
    description=(
        "Based on the financial analysis already performed, provide an investment perspective. "
        "User query: {query}\n\n"
        "Your investment analysis must:\n"
        "1. Evaluate the company's financial health based solely on document data\n"
        "2. Identify investment strengths (e.g., strong free cash flow, improving margins)\n"
        "3. Identify investment concerns (e.g., rising debt, declining revenue)\n"
        "4. Provide a balanced view of the investment case — bullish and bearish factors\n"
        "5. NOT provide personalized investment advice or specific buy/sell recommendations\n\n"
        "All points must reference specific figures from the financial document. "
        "Include a disclaimer that this is not personalized financial advice."
    ),
    expected_output=(
        "A balanced investment perspective report containing:\n"
        "- **Financial Health Score**: Brief qualitative assessment (Strong/Moderate/Weak) with justification\n"
        "- **Investment Strengths**: Bullet list of positive indicators with supporting data\n"
        "- **Investment Concerns**: Bullet list of risk indicators with supporting data\n"
        "- **Key Metrics Summary**: P/E, EV/EBITDA, debt-to-equity, or other relevant ratios if available\n"
        "- **Disclaimer**: Statement that this analysis is informational only and not personalized investment advice\n\n"
        "Do not recommend specific securities, funds, or financial products. "
        "Do not fabricate metrics not present in the document."
    ),
    agent=investment_advisor,
    tools=[FinancialDocumentTool.read_data_tool],
    async_execution=False,
)

## Creating a risk assessment task
# Bug Fix #12: was `agent=financial_analyst` → correct agent is `risk_assessor`
risk_assessment = Task(
    description=(
        "Perform a structured risk assessment based on the financial document. "
        "User query: {query}\n\n"
        "Identify and assess the following risk categories using evidence from the document:\n"
        "1. **Market Risk**: Exposure to interest rates, FX, commodity prices\n"
        "2. **Credit Risk**: Counterparty exposure, accounts receivable quality, debt obligations\n"
        "3. **Liquidity Risk**: Short-term obligations vs. available cash, current ratio\n"
        "4. **Operational Risk**: Supply chain, regulatory, or operational challenges mentioned\n"
        "5. **Strategic Risk**: Competitive threats, market share trends, guidance revisions\n\n"
        "Base every risk finding on data explicitly stated in the document. "
        "Rate each risk category as Low, Medium, or High with a brief justification."
    ),
    expected_output=(
        "A structured risk assessment report containing:\n"
        "- **Overall Risk Profile**: Composite risk level (Low/Medium/High) with summary\n"
        "- **Risk Category Breakdown**: For each of the 5 categories — rating, key risk factors, evidence from document\n"
        "- **Key Risk Metrics**: Relevant ratios (current ratio, debt-to-equity, interest coverage) if available\n"
        "- **Mitigating Factors**: Any risk mitigation strategies mentioned by management\n"
        "- **Disclaimer**: Risk assessment based on publicly disclosed document data only\n\n"
        "Do not invent risk scenarios not supported by the document. "
        "Do not recommend specific hedging products or financial strategies."
    ),
    agent=risk_assessor,
    tools=[FinancialDocumentTool.read_data_tool],
    async_execution=False,
)


## Creating a document verification task
# Bug Fix #10: was `agent=financial_analyst` → correct agent is `verifier`
verification = Task(
    description=(
        "Verify that the uploaded file is a legitimate financial document. "
        "The document is located at this EXACT file path: {file_path}\n\n"
        "Use the Financial Document Reader tool with path='{file_path}' to inspect its content. "
        "Check for the presence of standard financial report elements:\n"
        "- Company name, reporting period, and currency\n"
        "- At least one of: income statement, balance sheet, cash flow statement\n"
        "- Financial figures, tables, or numerical data\n"
        "- Management discussion or notes to financial statements\n\n"
        "If the document does NOT contain financial information, clearly state this and "
        "explain what type of document it appears to be."
    ),
    expected_output=(
        "A verification report containing:\n"
        "- **Verification Status**: VERIFIED / UNVERIFIED / PARTIAL\n"
        "- **Document Type**: What type of financial document this appears to be (e.g., quarterly earnings, annual report, 10-K)\n"
        "- **Key Elements Found**: List of financial components identified\n"
        "- **Missing Elements**: Any expected components not found\n"
        "- **Recommendation**: Whether to proceed with full financial analysis\n\n"
        "Be accurate and honest. Do not classify non-financial documents as financial reports."
    ),
    agent=verifier,
    tools=[FinancialDocumentTool.read_data_tool],
    async_execution=False
)