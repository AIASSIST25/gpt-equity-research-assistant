# equity_gpt_assistant.py (FMP-only version)
from openai import OpenAI
import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
FMP_API_KEY = "ds6lNQx3yC9qUEGFr69silY24hligX"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def query_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def get_company_summary(ticker):
    url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={FMP_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200 and response.json():
        return response.json()[0].get("description", "No summary available.")
    return "No summary available."

def get_fmp_financials(ticker):
    def fetch_json(url):
        r = requests.get(url)
        return r.json() if r.status_code == 200 else []

    income_url = f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}?limit=5&apikey={FMP_API_KEY}"
    balance_url = f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker}?limit=5&apikey={FMP_API_KEY}"
    cashflow_url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?limit=5&apikey={FMP_API_KEY}"
    dividend_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/stock_dividend/{ticker}?apikey={FMP_API_KEY}"

    income = fetch_json(income_url)
    balance = fetch_json(balance_url)
    cashflow = fetch_json(cashflow_url)
    dividends = fetch_json(dividend_url)

    return income, balance, cashflow, dividends

def run_business_analysis(ticker):
    summary = get_company_summary(ticker)
    prompt = f"""
You are an equity research analyst. Based on the company summary below, answer:

1. What are the company’s main products/services?
2. How does it make money?
3. What are its key customer and geographic segments?
4. Are there any major dependencies or risks?

Company Summary:
{summary}
"""
    return query_gpt(prompt)

def run_financial_analysis(ticker):
    income, balance, cashflow, dividends = get_fmp_financials(ticker)
    if not income or not cashflow:
        return "Missing financial data", pd.DataFrame(), pd.Series([0])

    df = pd.DataFrame({
        'Year': [i['calendarYear'] for i in income],
        'Revenue': [i.get('revenue', 0) for i in income],
        'Gross Profit': [i.get('grossProfit', 0) for i in income],
        'EBITDA': [i.get('ebitda', 0) for i in income],
        'Net Income': [i.get('netIncome', 0) for i in income],
        'Operating Cash Flow': [c.get('operatingCashFlow', 0) for c in cashflow],
        'CapEx': [c.get('capitalExpenditure', 0) for c in cashflow],
        'Free Cash Flow': [c.get('operatingCashFlow', 0) - c.get('capitalExpenditure', 0) for c in cashflow]
    })

    div_df = pd.DataFrame(dividends.get("historical", []))
    div_df["year"] = pd.to_datetime(div_df["date"]).dt.year
    dividend_summary = div_df.groupby("year")["dividend"].sum()

    df["Dividends"] = df["Year"].astype(int).map(dividend_summary.to_dict()).fillna(0)

    prompt = f"""
You're reviewing historical financials for a company.

Based on this data, answer:

1. Revenue growth trend
2. Margins (gross, EBITDA, net income)
3. Free cash flow trends
4. Dividend payment trend
5. Debt and liquidity position

Financials:
{df.to_string()}
"""
    return query_gpt(prompt), df, df["Free Cash Flow"]

def run_dcf_analysis(fcf, wacc=8.0, terminal_growth=2.5):
    fcf_forecast = fcf.head(5).fillna(0)
    dcf_prompt = f"""
You're performing a DCF valuation.

Use the following Free Cash Flows, WACC of {wacc}%, and terminal growth rate of {terminal_growth}% to calculate:
1. Enterprise value
2. Equity value
3. Implied share price

Free Cash Flows:
{fcf_forecast.to_string()}
"""
    return query_gpt(dcf_prompt)

def get_filing_summary(ticker):
    url = f"https://financialmodelingprep.com/api/v3/sec_filings/{ticker}?type=10-K&limit=1&apikey={FMP_API_KEY}"
    filings = requests.get(url).json()
    if not filings:
        return "No 10-K filings found."
    if isinstance(filings, list) and len(filings) > 0 and 'link' in filings[0]:
        filing_url = filings[0]['link']
    else:
        return 'No valid 10-K filing found.'
    if not filing_url:
        return "10-K link not available."
    filing_text = requests.get(filing_url).text
    soup = BeautifulSoup(filing_text, "html.parser")

def export_to_excel(business_analysis, financial_analysis, fin_df, dcf_result, ticker):
    with pd.ExcelWriter(f"{ticker}_equity_report.xlsx") as writer:
        pd.DataFrame({'Business Summary': [business_analysis]}).to_excel(writer, sheet_name="Business", index=False)
        pd.DataFrame({'Financial Analysis': [financial_analysis]}).to_excel(writer, sheet_name="Financials", index=False)
        pd.DataFrame({'DCF Result': [dcf_result]}).to_excel(writer, sheet_name="Valuation", index=False)
        fin_df.to_excel(writer, sheet_name="Raw Data")

# Streamlit App
st.title("GPT-Powered Equity Research Assistant (FMP Edition)")
ticker = st.text_input("Enter Ticker Symbol:", value="AAPL")
if st.button("Run Analysis"):
    with st.spinner("Running analysis..."):
        business_analysis = run_business_analysis(ticker)
        financial_analysis, fin_df, fcf_data = run_financial_analysis(ticker)
        dcf_result = run_dcf_analysis(fcf_data)
        tenk_summary = get_filing_summary(ticker)
        export_to_excel(business_analysis, financial_analysis, fin_df, dcf_result, ticker)

        st.subheader("Business Analysis")
        st.write(business_analysis)

        st.subheader("Financial Analysis")
        st.write(financial_analysis)

        st.subheader("DCF Valuation")
        st.write(dcf_result)

        st.subheader("10-K Summary")
        st.write(tenk_summary)

        st.success(f"Excel report saved as {ticker}_equity_report.xlsx")
