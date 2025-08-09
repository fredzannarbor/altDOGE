# AltDOGE: An Open-Source Platform for Customizable Regulatory Reform

## Vision
AltDOGE democratizes AI in government by enabling "Bring Your Own Models" to the same data that the Department of Government Efficiency (DOGE) is analyzing with its large language models.  

### Latest - 8/8/2025

Ran v0.2.0 against 485 documents in the Community Living Administration's section of the CFR at a cost of ~$5 using gemini-2.5-flash. Analyzed all 485 docs using prompts similar to DOGE.

<img width="907" height="1027" alt="Screenshot 2025-08-09 at 04 37 47" src="https://github.com/user-attachments/assets/7ce76cab-db5a-4eea-9ac7-2bec9ae7c994" />


### AltDOGE "First Steps" - **④**

This release is a proof of concept to match [DOGE's regulatory reform initiative recently discussed in the Washington Post](https://wapo.st/45d5gqL).  In a nutshell, DOGE is using LLMs to analyze the Federal Register and cue it up for massive editing. They have a pretty simple process: assess whether the regulation is statutorily required and if it is not, whether the agency needs it anyway. I was able to simulate this in prompts.

```
{
  "DOGE Criteria": [
    "Analyze the following regulation text and categorize as Statutorily Required (SR), Not Statutorily Required (NSR), or Not Required but Agency Needs (NRAN). Provide a detailed justification citing statutory provisions if applicable:\n{text}",
    "Evaluate the following regulation for potential reform actions (deletion, simplification, harmonization, modernization). Suggest specific changes with justifications:\n{text}"]
}
```

In future releases we can emulate how the agencies and stakeholders respond to the recommendations.

I also (and this is the really cool part) demonstrated how an alternate strategy might interpret the same data with likely very different outcomes.

```
{
"Congress Meant to Act Effectively": [
    "Statutory Alignment: Ensure the regulation fully implements the statutory requirements and intent, addressing all mandated objectives without omission.\n{text}",
    "Clarity and Accessibility: Enhance the regulation\u2019s language and structure to make its purpose and implentation strategy clear, concise, and understandable to the general public.\n{text}",
    "Outcome: Evaluate whether the regulation achieves the outcomes Congress intended in authorizing the regulation. Assume that Congress meant for agencies to act effectively in this domain.  Include expert assessment and public sentiment.\n{text}",
    "Adaptability to Modern Contexts: Identify opportunities to update the regulation so that the effective scope of the legislation fully adapts to current technological, economic, political and social conditions.\n{text}"
  ]
}
```

### AltDOGE Next Steps

On a very specific level, some immediate practical steps that are essential to make this work:

- validate that my DOGE prompt strategy yields same results against HUD data as DOGE's
- sanity test my "Congress Meant It" strategy agains the same data
- invite regulatory stakeholders to develop strategy suites, and test them against subsets organized by agency (sorted by agency most likely to be targeted next?)

At a higher level, the AltDOGE vision is to let there be free and open competition in the analytic use of AI on government data.  By one SWAG, there are [approximately 5 billion tokens in the Federal Register.](https://grok.com/share/bGVnYWN5_d7fce4c0-f3bd-4739-bb78-6be6a3626bfe) There are comparably vast stores of other vital government data, including a whole-of-government data fusion effort currently only AI-accessible by DOGE. If we are to foreclose a potential AI-powered tyranny that might last "a thousand years", that imbalance must be remedied, and swiftly.    Neither I nor any ordinary individual can fund the expense of running millions of queries against billions of tokens, so **I strongly encourage high-net-worth individuals and frontier model operators to join me.**  The team to do this would involve a handful of AI-wrangling coders, data scientists, and policy networkers, plus a couple of months of my time to solve the main conceptual problems, get a system set up, and set it spinning. My email is wfzimmerman@gmail.com, my Signal is fredzannarbor.64.

## Features
- **Multi-Page Web Application**: A Streamlit-based dashboard for all user interactions.
  - Secure login for authenticated users.
  - **Ingest Data**: Fetch documents from the Federal Register for a given date range and agency.
  - **View Ingestion Results**: Review the detailed, multi-prompt analysis for each document in a specific run.
  - **Analyze Regulation**: Re-run analysis on any single, already-ingested regulation from the database.
  - **Review Summary**: A consolidated dashboard showing a high-level, actionable summary of all unique regulations analyzed.
  - **Public Dashboard**: A read-only, public-facing page to view cached analysis results without needing to log in.
- **Customizable Analytical Engine**:
  - **Prompt Strategies**: Define and switch between different analytical frameworks by editing a simple `prompt_strategies.json` file. No code changes needed to change the analysis.
  - **Meta-Analysis**: After running the base prompts, a second AI call synthesizes the results into a high-level summary, including a recommended action, goal alignment, and a bullet-point summary.
- **CLI for Batch Processing**: Ingest and analyze data via the command line for automated workflows.
- **Local Database**: Uses SQLite to store ingested regulations for re-analysis and persistence.
- **Open-Source**: Licensed under Apache 2.0.

## Setup Instructions
1.  **Clone the repository** (if not already done):
    
2. Run the initialization script: `python init_altdoge.py`
   - This script creates the repository structure, installs Python 3.12.3 (if needed), installs uv and dependencies, initializes the database, sets up environment variables, and initializes a Git repository.
3. Run the application: `python run_altdoge.py --mode app`
   - Access the app at `http://localhost:8501`.
   - To ingest Federal Register data: `python run_altdoge.py --mode ingest --start-date 2025-01-20`

## Requirements
- Python 3.12.3 (automatically installed by `init_altdoge.py`)
- uv 0.4.24 (installed by `init_altdoge.py`)
- SQLite (`xtuff_collections.db`)
- See `requirements.txt` for dependencies.

## Environment Variables
The `init_altdoge.py` script creates a `.env` file, prompting for:
```
STRIPE_API_KEY=your_stripe_api_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
LITELLM_MODEL=gpt-4o
LITELLM_API_KEY=your_llm_api_key
FEDERAL_REGISTER_API_KEY=your_federal_register_api_key
```

## Contribution Guidelines
- Follow the [Contribution Guide](CONTRIBUTING.md) (TBD).
- Submit issues and pull requests via GitHub.
- Join our community forum (TBD) for discussions.

## License
Apache 2.0 License
