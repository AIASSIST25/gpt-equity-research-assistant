# equity_gpt_assistant.py
import yfinance as yf
import openai
import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup
import openpyxl

openai.api_key = "YOUR_OPENAI_API_KEY"

def query_gpt(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

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

def get_company_summary(ticker):
    yf_ticker = yf.Ticker(ticker)
    return yf_ticker.info.get('longBusinessSummary', 'No summary available.')

def get_financials(ticker):
    t = yf.Ticker(ticker)
    income = t.financials
    balance = t.balance_sheet
    cashflow = t.cashflow
    dividends = t.dividends
    return income, balance, cashflow, dividends

def run_business_analysis(ticker):
    summary = get_company_summary(ticker)
    prompt = build_business_prompt(summary)
    return query_gpt(prompt)

def run_financial_analysis(ticker):
    income, balance, cashflow, dividends = get_financials(ticker)
    fcf = cashflow.loc['Total Cash From Operating Activities'] - cashflow.loc['Capital Expenditures']
    fin_df = pd.DataFrame({
        'Revenue': income.loc['Total Revenue'],
        'Net Income': income.loc['Net Income'],
        'Operating Cash Flow': cashflow.loc['Total Cash From Operating Activities'],
        'CapEx': cashflow.loc['Capital Expenditures'],
        'Free Cash Flow': fcf,
        'Dividends': dividends.groupby(dividends.index.year).sum()
    })
    prompt = build_financial_prompt(fin_df)
    return query_gpt(prompt), fin_df

def scrape_10k_summary(ticker):
    cik_lookup = requests.get(f'https://www.sec.gov/files/company_tickers.json').json()
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
    return query_gpt(f"Summarize this 10-K filing:\n{text[:10000]}")  # Limit to first 10,000 characters

def export_to_excel(business_analysis, financial_analysis, fin_df, ticker):
    with pd.ExcelWriter(f"{ticker}_equity_report.xlsx") as writer:
        pd.DataFrame({'Business Summary': [business_analysis]}).to_excel(writer, sheet_name="Business", index=False)
        pd.DataFrame({'Financial Analysis': [financial_analysis]}).to_excel(writer, sheet_name="Financials", index=False)
        fin_df.to_excel(writer, sheet_name="Raw Data")

# Streamlit App
st.title("GPT-Powered Equity Research Assistant")
ticker = st.text_input("Enter Ticker Symbol:", value="ACGL")
if st.button("Run Analysis"):
    with st.spinner("Analyzing..."):
        business_analysis = run_business_analysis(ticker)
        financial_analysis, fin_df = run_financial_analysis(ticker)
        tenk_summary = scrape_10k_summary(ticker)
        export_to_excel(business_analysis, financial_analysis, fin_df, ticker)

        st.subheader("Business Analysis")
        st.write(business_analysis)

        st.subheader("Financial Analysis")
        st.write(financial_analysis)

        st.subheader("10-K Summary")
        st.write(tenk_summary)

        st.success(f"Report exported to {ticker}_equity_report.xlsx")
