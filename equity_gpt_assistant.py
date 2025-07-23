# equity_gpt_assistant.py
import yfinance as yf
from openai import OpenAI
import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup
import openpyxl
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
FMP_API_KEY = "ds6lNQx3yC9qUEGFr69silY24hligX"

def query_gpt(prompt):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def build_business_prompt(summary_text):
    return f"""
You are an equity research analyst. Based on the company summary below, answer:

1. What are the company’s main products/services?
2. How does it make money?
3. What are its key customer and geographic segments?
4. Are there any major dependencies or risks?

Company Summary:
{summary_text}
"""

def get_company_summary(ticker):
    url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={FMP_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200 and response.json():
        return response.json()[0].get("description", "No summary available.")
    return "No summary available."

def build_financial_prompt(financial_df):
    return f"""
You're reviewing historical financials for an insurance company.

Based on this data, answer:

1. Revenue growth trend
2. Margins (gross, EBITDA, net income)
3. Free cash flow trends
4. Dividend payment trend
5. Debt and liquidity position

Financials:
{financial_df.to_string()}
"""

def build_dcf_prompt(fcf_data, wacc, terminal_growth):
    return f"""
You're performing a DCF valuation.

Use the following Free Cash Flows, WACC of {wacc}%, and terminal growth rate of {terminal_growth}% to calculate:
1. Enterprise value
2. Equity value
3. Implied share price

Free Cash Flows:
{fcf_data.to_string()}
"""

def get_financials(ticker):
    t = yf.Ticker(ticker)
    income = t.financials
    balance = t.balance_sheet
    cashflow = t.cashflow
    dividends = t.dividends

    operating_cf = cashflow.loc['Total Cash From Operating Activities'] if 'Total Cash From Operating Activities' in cashflow.index else pd.Series([0]*4)
    capex = cashflow.loc['Capital Expenditures'] if 'Capital Expenditures' in cashflow.index else pd.Series([0]*4)
    fcf = operating_cf - capex

    return income, balance, cashflow, dividends, fcf

def run_business_analysis(ticker):
    summary = get_company_summary(ticker)
    prompt = build_business_prompt(summary)
    return query_gpt(prompt)

def run_financial_analysis(ticker):
    income, balance, cashflow, dividends, fcf = get_financials(ticker)
    fin_df = pd.DataFrame({
        'Revenue': income.loc['Total Revenue'] if 'Total Revenue' in income.index else pd.Series([0]*4),
        'Net Income': income.loc['Net Income'] if 'Net Income' in income.index else pd.Series([0]*4),
        'Operating Cash Flow': cashflow.loc['Total Cash From Operating Activities'] if 'Total Cash From Operating Activities' in cashflow.index else pd.Series([0]*4),
        'CapEx': cashflow.loc['Capital Expenditures'] if 'Capital Expenditures' in cashflow.index else pd.Series([0]*4),
        'Free Cash Flow': fcf,
        'Dividends': dividends.groupby(dividends.index.year).sum() if not dividends.empty else pd.Series([0])
    })
    prompt = build_financial_prompt(fin_df)
    return query_gpt(prompt), fin_df, fcf

def run_dcf_analysis(fcf, wacc=8.0, terminal_growth=2.5):
    fcf_forecast = fcf.head(5).fillna(0)
    dcf_prompt = build_dcf_prompt(fcf_forecast, wacc, terminal_growth)
    return query_gpt(dcf_prompt)

def scrape_10k_summary(ticker):
    try:
    resp = requests.get("https://www.sec.gov/files/company_tickers.json")
    cik_lookup = resp.json()
    except Exception as e:
    return f"Error retrieving CIK lookup from SEC: {e}"
    cik = None
    for record in cik_lookup.values():
        if record['ticker'].upper() == ticker.upper():
            cik = str(record['cik_str']).zfill(10)
            break
    if not cik:
        return "CIK not found."
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/index.json"
    index_data = requests.get(url).json()
    for file in index_data['directory']['item']:
        if '10-k' in file['name'].lower():
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{file['name']}"
            break
    else:
        return "10-K not found."
    filing = requests.get(doc_url).text
    soup = BeautifulSoup(filing, 'html.parser')
    text = soup.get_text()
    return query_gpt(f"Summarize this 10-K filing:\n{text[:10000]}")

def export_to_excel(business_analysis, financial_analysis, fin_df, dcf_result, ticker):
    with pd.ExcelWriter(f"{ticker}_equity_report.xlsx") as writer:
        pd.DataFrame({'Business Summary': [business_analysis]}).to_excel(writer, sheet_name="Business", index=False)
        pd.DataFrame({'Financial Analysis': [financial_analysis]}).to_excel(writer, sheet_name="Financials", index=False)
        pd.DataFrame({'DCF Result': [dcf_result]}).to_excel(writer, sheet_name="Valuation", index=False)
        fin_df.to_excel(writer, sheet_name="Raw Data")

# Streamlit App
st.title("GPT-Powered Equity Research Assistant")
ticker = st.text_input("Enter Ticker Symbol:", value="ACGL")
if st.button("Run Analysis"):
    with st.spinner("Analyzing..."):
        business_analysis = run_business_analysis(ticker)
        financial_analysis, fin_df, fcf_data = run_financial_analysis(ticker)
        dcf_result = run_dcf_analysis(fcf_data)
        tenk_summary = scrape_10k_summary(ticker)
        export_to_excel(business_analysis, financial_analysis, fin_df, dcf_result, ticker)

        st.subheader("Business Analysis")
        st.write(business_analysis)

        st.subheader("Financial Analysis")
        st.write(financial_analysis)

        st.subheader("DCF Valuation")
        st.write(dcf_result)

        st.subheader("10-K Summary")
        st.write(tenk_summary)

        st.success(f"Report exported to {ticker}_equity_report.xlsx")
