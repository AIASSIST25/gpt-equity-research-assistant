# GPT Equity Research Assistant 🧠📊

This is an AI-powered equity research assistant that automates fundamental analysis using GPT-4, financial APIs, and a Streamlit dashboard. It performs business model analysis, financial trend review, 10-K summarization, and exports a structured Excel report.

---

## 🚀 Features

- 🔎 **Business Analysis** — GPT summarizes company model, revenue sources, and geographic exposure
- 📈 **Financial Trend Review** — Revenue, net income, FCF, dividends, debt, and liquidity
- 📄 **10-K Scraper & Summarizer** — Pulls and summarizes the latest SEC 10-K filing
- 📊 **Excel Export** — Structured output for further analysis or sharing
- 🖥️ **Streamlit UI** — Run as an interactive app on your machine or Streamlit Cloud

---

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/AIASSIST25/gpt-equity-research-assistant.git
cd gpt-equity-research-assistant
```

### 2. Create a virtual environment (optional but recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Mac/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Variables

Create a `.env` file with your [OpenAI API key](https://platform.openai.com/account/api-keys):

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

The script uses `dotenv` to load this securely.

---

## 🧪 Run the Assistant

```bash
streamlit run equity_gpt_assistant.py
```

---

## 📤 Output

- Excel file: `ACGL_equity_report.xlsx`
- Contains:
  - GPT business summary
  - Financial trend analysis
  - Raw revenue, FCF, dividends
  - 10-K summarization

---

## 🧠 Tech Stack

- Python
- OpenAI GPT-4
- yFinance API
- SEC EDGAR Scraper
- Streamlit
- pandas, openpyxl, BeautifulSoup

---

## 📬 Coming Soon

- DCF Valuation + Comps
- Scenario Analysis (Bull/Base/Bear)
- Auto-generated Investment Thesis + Price Target
- Email or Notion integration

---

## 📄 License

MIT License

---

## 🙌 Author

Built with discipline and hustle by [David Costa](https://github.com/AIASSIST25) ⚔️
