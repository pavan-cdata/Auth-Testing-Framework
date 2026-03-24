# CData Auth Testing Framework

An AI-powered CLI tool for automated JDBC authentication testing against CData drivers. It discovers auth schemes from a driver JAR, fetches credentials from 1Password, generates intelligent test cases using Groq AI, executes JDBC connection tests, and exports results to a formatted Excel report.

---

## How It Works — Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                     python src/main.py                          │
│                  --driver pipedrive                             │
│                  --creds "pipedrive item"                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
            ┌──────────────▼──────────────┐
            │   1. Load JDBC Driver JAR   │
            │   (CData installed driver)  │
            └──────────────┬──────────────┘
                           │
            ┌──────────────▼──────────────┐
            │   2. Discover Auth Schemes  │
            │   via getPropertyInfo()     │
            │   e.g. [OAuth, Basic]       │
            └──────────────┬──────────────┘
                           │
            ┌──────────────▼──────────────┐
            │   3. Fetch Credentials      │
            │   from 1Password CLI (op)   │
            │   Parses JDBC conn string   │
            └──────────────┬──────────────┘
                           │
            ┌──────────────▼──────────────┐
            │   4. Filter Fields          │
            │   Per auth scheme:          │
            │   - Strip OAuth fields for  │
            │     Basic auth              │
            │   - Strip Basic fields for  │
            │     OAuth                   │
            │   - Always strip proxy/SSL/ │
            │     infra fields            │
            └──────────────┬──────────────┘
                           │
            ┌──────────────▼──────────────┐
            │   5. Generate Test Cases    │
            │   Groq AI (llama-3.3-70b)   │
            │   receives field NAMES only │
            │   (no credential values)    │
            │   Returns smart mutations:  │
            │   - Missing fields          │
            │   - Invalid values          │
            │   - Empty values            │
            │   - Edge cases per scheme   │
            └──────────────┬──────────────┘
                           │
            ┌──────────────▼──────────────┐
            │   6. Execute JDBC Tests     │
            │   JPype → DriverManager     │
            │   .getConnection(url)       │
            │   Returns SUCCESS or error  │
            └──────────────┬──────────────┘
                           │
            ┌──────────────▼──────────────┐
            │   7. Analyze Results        │
            │   PASS / FAIL / BUG         │
            └──────────────┬──────────────┘
                           │
            ┌──────────────▼──────────────┐
            │   8. Export Excel Report    │
            │   reports/<driver>_<ts>.xlsx│
            │   + Console summary         │
            └─────────────────────────────┘
```

---

## Project Structure

```
cdata-auth-testing-ai/
│
├── src/
│   ├── main.py                  # CLI entry point, orchestrates the workflow
│   ├── driver_inspector.py      # Loads JAR via JPype, discovers AuthSchemes
│   ├── credential_fetcher.py    # Fetches & parses credentials from 1Password
│   ├── test_case_generator.py   # Asks Groq AI to generate test case scenarios
│   ├── executor.py              # Runs JDBC connections via java.sql.DriverManager
│   ├── analyzer.py              # Classifies results: PASS / FAIL / BUG
│   └── report.py                # Prints console output + exports Excel file
│
├── config/
│   └── limits.json              # Max test cases, query, timeout settings
│
├── reports/                     # Auto-generated Excel reports (gitignored)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Python 3.12 or 3.13** | JPype1 requires a prebuilt wheel (not available for 3.14) |
| **Java JDK** | Required by JPype to run the JVM |
| **CData JDBC Driver** | Installed at `C:\Program Files\CData\CData JDBC Driver for <Driver> 2025\` |
| **1Password CLI (`op`)** | Must be installed and signed in |
| **Groq API Key** | Free at [console.groq.com](https://console.groq.com) |

---

## Setup

### 1. Clone the repo
```powershell
git clone https://github.com/pavan-cdata/Auth-Testing-Framework.git
cd Auth-Testing-Framework
```

### 2. Create virtual environment with Python 3.13
```powershell
py -3.13 -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies
```powershell
pip install -r requirements.txt
```

### 4. Set Groq API Key
```powershell
# Option A: Set manually
$env:GROQ_API_KEY = "gsk_your_key_here"

# Option B: Fetch from 1Password
$env:GROQ_API_KEY = (op item get "groq key copilot" --fields notesPlain)
```

### 5. Add 1Password to PATH (if `op` not found)
```powershell
$env:PATH += ";C:\Users\<YourUser>\AppData\Local\Microsoft\WinGet\Packages\AgileBits.1Password.CLI_Microsoft.Winget.Source_8wekyb3d8bbwe"
```

---

## Usage

```powershell
python src/main.py --driver <driver_name> --creds "<1password_item_name>" [--limit N]
```

### Arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `--driver` | Yes | — | Driver name (e.g. `shopify`, `pipedrive`) |
| `--creds` | No | `{driver}_creds` | 1Password item name containing the JDBC connection string |
| `--limit` | No | `25` | Max test cases per auth scheme |

### Examples

```powershell
# Pipedrive — all test cases
python src/main.py --driver pipedrive --creds "pipedrive najmurcompany"

# Shopify — limit 10 cases per scheme
python src/main.py --driver shopify --creds "shopify_item" --limit 10

# Any CData driver
python src/main.py --driver salesforce --creds "salesforce creds"
```

---

## 1Password Credential Format

The tool expects the 1Password item to contain either:

**A. A JDBC connection string in the Notes field** (preferred):
```
jdbc:pipedrive:InitiateOAuth=GETANDREFRESH;OAuthClientId=xxx;OAuthClientSecret=yyy;CompanyDomain=https://company.pipedrive.com/;Schema=Pipedrive;
```

**B. Individual labeled fields** — the tool reads each field's label and value directly.

---

## JAR Path Convention

The driver JAR is resolved automatically from the driver name:

```
C:\Program Files\CData\CData JDBC Driver for {Driver} 2025\lib\cdata.jdbc.{driver}.jar
```

| `--driver` | JAR resolved |
|---|---|
| `shopify` | `...CData JDBC Driver for Shopify 2025\lib\cdata.jdbc.shopify.jar` |
| `pipedrive` | `...CData JDBC Driver for Pipedrive 2025\lib\cdata.jdbc.pipedrive.jar` |
| `salesforce` | `...CData JDBC Driver for Salesforce 2025\lib\cdata.jdbc.salesforce.jar` |

---

## Field Filtering Logic

The tool automatically strips irrelevant fields per auth scheme to keep test cases focused:

| Field Category | Stripped when |
|---|---|
| OAuth fields (`OAuthClientId`, `OAuthClientSecret`, `InitiateOAuth`, etc.) | Scheme is NOT OAuth |
| Basic auth fields (`APIKey`, `User`, `Password`, etc.) | Scheme IS OAuth |
| Infrastructure fields (`ProxyServer`, `ProxyPort`, `SSLServerCert`, `FirewallServer`, etc.) | **Always** stripped |

---

## Excel Report

Reports are saved in `reports/<driver>_<timestamp>.xlsx` with two sheets:

**Sheet 1 — Auth Test Results**

| Column | Description |
|---|---|
| S.No | Row number |
| Auth Scheme | e.g. OAuth, Basic |
| Test Case | AI-generated description of what is being tested |
| Connection String | Full JDBC URL used for the test |
| Pass/Fail | Green = PASS, Red = FAIL |
| Driver Response / Error Message | Full error from the driver on failure |
| Comments | Auto-flags like "Potential bug" or "Verify if expected" |

**Sheet 2 — Summary**

| Field | Value |
|---|---|
| Driver | Driver name |
| Date | Run timestamp |
| Total Test Cases | Total count |
| Passed | Count |
| Failed | Count |
| Bugs Found | Count of NullPointerException or unexpected errors |

---

## Security Notes

- **Credentials are never sent to Groq AI** — only field *names* are sent (e.g. `["OAuthClientId", "Schema"]`)
- The `GROQ_API_KEY` is read from the environment variable, never hardcoded
- `reports/` and `.env` are gitignored

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.13 |
| JDBC Bridge | `jpype1` |
| 1Password | `op` CLI (`subprocess`) |
| AI Test Generation | Groq API (`llama-3.3-70b-versatile`) |
| Excel Reports | `openpyxl` |
| CLI | `argparse` |
