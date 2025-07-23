
# Patched equity_gpt_assistant.py with fallback logic and partial financial support
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
    try:
        data = response.json()
        if data and isinstance(data, list):
            return data[0].get("description", "No summary available.")
    except:
        pass
    return f"What does {ticker} do? Provide an investor-oriented summary."

def get_fmp_financials(ticker):
    def fetch_json(url):
        r = requests.get(url)
        try:
            return r.json() if r.status_code == 200 else []
        except:
            return []

    income = fetch_json(f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}?limit=5&apikey={FMP_API_KEY}")
    balance = fetch_json(f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker}?limit=5&apikey={FMP_API_KEY}")
    cashflow = fetch_json(f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?limit=5&apikey={FMP_API_KEY}")
    dividends = fetch_json(f"https://financialmodelingprep.com/api/v3/historical-price-full/stock_dividend/{ticker}?apikey={FMP_API_KEY}")
    return income, balance, cashflow, dividends

def run_financial_analysis(ticker):
    income, balance, cashflow, dividends = get_fmp_financials(ticker)

    if not any([income, balance, cashflow]):
        return "Missing financial data", pd.DataFrame(), pd.Series([0])

    df = pd.DataFrame()
    if income:
        df["Year"] = [i['calendarYear'] for i in income]
        df["Revenue"] = [i.get('revenue', 0) for i in income]
        df["Gross Profit"] = [i.get('grossProfit', 0) for i in income]
        df["EBITDA"] = [i.get('ebitda', 0) for i in income]
        df["Net Income"] = [i.get('netIncome', 0) for i in income]

    if cashflow:
        df["Operating CF"] = [c.get('operatingCashFlow', 0) for c in cashflow]
        df["CapEx"] = [c.get('capitalExpenditure', 0) for c in cashflow]
        df["Free Cash Flow"] = df["Operating CF"] - df["CapEx"]

    if balance:
        df["Total Debt"] = [b.get('totalDebt', 0) for b in balance]
        df["Cash & Equiv"] = [b.get('cashAndCashEquivalents', 0) for b in balance]
        df["Total Assets"] = [b.get('totalAssets', 0) for b in balance]
        df["Total Equity"] = [b.get('totalStockholdersEquity', 0) for b in balance]
        df["Current Ratio"] = [b.get('totalCurrentAssets', 0) / b.get('totalCurrentLiabilities', 1) for b in balance]

    if "Gross Profit" in df and "Revenue" in df:
        df["Gross Margin"] = df["Gross Profit"] / df["Revenue"]
    if "EBITDA" in df and "Revenue" in df:
        df["EBITDA Margin"] = df["EBITDA"] / df["Revenue"]
    if "Net Income" in df and "Revenue" in df:
        df["Net Margin"] = df["Net Income"] / df["Revenue"]
    if "Net Income" in df and "Total Equity" in df:
        df["ROE"] = df["Net Income"] / df["Total Equity"].replace(0, 1)
    if "Net Income" in df and "Total Assets" in df:
        df["ROA"] = df["Net Income"] / df["Total Assets"].replace(0, 1)
    if "Total Debt" in df and "Total Equity" in df:
        df["Debt/Equity"] = df["Total Debt"] / df["Total Equity"].replace(0, 1)

    div_df = pd.DataFrame(dividends.get("historical", []))
    if not div_df.empty:
        div_df["year"] = pd.to_datetime(div_df["date"]).dt.year
        dividend_summary = div_df.groupby("year")["dividend"].sum()
        df["Dividends"] = df["Year"].astype(int).map(dividend_summary.to_dict()).fillna(0)

    prompt = f"""
You are reviewing historical financials.

Discuss revenue, margins, free cash flow, leverage and dividends based on:

{df.to_string()}
"""
    return query_gpt(prompt), df, df.get("Free Cash Flow", pd.Series([0]))

def run_business_analysis(ticker):
    summary = get_company_summary(ticker)
    prompt = f"""
You are an equity research analyst. Based on the company summary below, answer:

1. What are the company’s main products/services?
2. How does it make money?
3. Who are its customers and in which geographies does it operate?
4. Are there any major risks or dependencies?

Company Summary:
{summary}
"""
    return query_gpt(prompt)

def run_dcf_analysis(fcf, wacc=8.0, terminal_growth=2.5):
    valid_fcf = fcf.dropna().head(5)
    if valid_fcf.sum() == 0:
        return "Free cash flow data missing — unable to run DCF."

    prompt = f"""
You're performing a DCF valuation.

Use these FCFs, WACC of {wacc}%, and terminal growth of {terminal_growth}% to estimate:

- Enterprise Value
- Equity Value
- Share Price

Free Cash Flows:
{valid_fcf.to_string()}
"""
    return query_gpt(prompt)

def get_filing_summary(ticker):
    url = f"https://financialmodelingprep.com/api/v3/sec_filings/{ticker}?limit=5&apikey={FMP_API_KEY}"
    filings = requests.get(url).json()
    valid = [f for f in filings if '10-K' in f.get('title', '').upper()]
    if valid:
        filing_url = valid[0].get("link", "")
    else:
        return "No valid 10-K filing found."

    try:
        filing_text = requests.get(filing_url).text
        soup = BeautifulSoup(filing_text, "html.parser")
        return query_gpt(f"Summarize this 10-K filing:\n{soup.get_text()[:10000]}")
    except Exception as e:
        return f"Error reading 10-K: {e}"

def export_to_excel(business_analysis, financial_analysis, fin_df, dcf_result, ticker):
    with pd.ExcelWriter(f"{ticker}_equity_report.xlsx") as writer:
        pd.DataFrame({'Business Summary': [business_analysis]}).to_excel(writer, sheet_name="Business", index=False)
        pd.DataFrame({'Financial Analysis': [financial_analysis]}).to_excel(writer, sheet_name="Financials", index=False)
        pd.DataFrame({'DCF Result': [dcf_result]}).to_excel(writer, sheet_name="Valuation", index=False)
        fin_df.to_excel(writer, sheet_name="Raw Data", index=False)

# Streamlit App
st.title("GPT-Powered Equity Research Assistant (Resilient Edition)")
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
