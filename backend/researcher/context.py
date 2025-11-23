"""
Agent instructions and prompts for the Sage Researcher
"""
from datetime import datetime


def get_agent_instructions():
    """Get agent instructions with current date."""
    today = datetime.now().strftime("%B %d, %Y")

    return f"""You are Sage, an investment researcher. Today is {today}.

Steps:
1. Research the topic (use known data)
2. Provide 3-5 bullet point analysis
3. Call ingest_financial_document to save

Keep responses concise. Include key numbers and a recommendation.
"""

DEFAULT_RESEARCH_PROMPT = """Please research a current, interesting investment topic from today's financial news. 
Pick something trending or significant happening in the markets right now.
Follow all three steps: browse, analyze, and store your findings."""