# src/ingestionmanager.py
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
import os
from datetime import datetime
from dotenv import load_dotenv
import logging
import backoff
from pathlib import Path
import sys
import urllib.parse
import json

# Set project root and add to sys.path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import Database
from src import llm_caller

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class LLMLimitReachedError(Exception):
    """Custom exception to signal that the LLM call limit has been reached."""
    pass


class IngestionManager:
    LLMLimitReachedError = LLMLimitReachedError

    def __init__(self, db: Database):
        self.db = db
        self.api_key = os.getenv("FEDERAL_REGISTER_API_KEY")
        self.base_url = "https://www.federalregister.gov/api/v1/documents"
        self.chunk_size = 100
        self.request_timeout = 30  # Timeout for HTTP requests
        self.llm_calls_made = 0
        self.llm_call_limit = None
        self.prompt_strategies = self._load_prompt_strategies()
        self.agencies = self._get_all_agencies()

    def _load_prompt_strategies(self) -> Dict[str, List[str]]:
        """Loads prompt strategies from a JSON file."""
        strategies_path = PROJECT_ROOT / "prompt_strategies.json"
        try:
            with open(strategies_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Could not load prompt strategies from {strategies_path}: {e}")
            # Return a default strategy as a fallback
            return {
                "DOGE Criteria": [
                    "Analyze the following regulation text and categorize as Statutorily Required (SR), Not Statutorily Required (NSR), or Not Required but Agency Needs (NRAN). Provide a detailed justification citing statutory provisions if applicable:\n{text}",
                    "Evaluate the following regulation for potential reform actions (deletion, simplification, harmonization, modernization). Suggest specific changes with justifications:\n{text}",
                    "Identify any outdated terminology or processes in the following regulation and propose modernized alternatives:\n{text}",
                    "Assess the clarity of the following regulation and suggest rephrasing to reduce ambiguity:\n{text}"
                ]
            }

    def _get_all_agencies(self) -> List[Dict[str, str]]:
        """Fetches a list of all agencies from the Federal Register API."""
        agencies_url = "https://www.federalregister.gov/api/v1/agencies"
        try:
            logger.info("Fetching list of all available agencies...")
            response = requests.get(agencies_url, timeout=self.request_timeout)
            response.raise_for_status()
            agencies_data = response.json()
            # Sort them alphabetically by name for the dropdown
            sorted_agencies = sorted(agencies_data, key=lambda x: x.get('name', ''))
            logger.info(f"Successfully fetched {len(sorted_agencies)} agencies.")
            return sorted_agencies
        except requests.exceptions.RequestException as e:
            logger.error(f"Could not fetch agency list: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Could not decode agency list JSON: {e}")
            return []

    def _get_meta_analysis(self, regulation_text: str, analysis_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Performs a meta-analysis on a set of prompt responses for a single regulation.
        """
        # Combine the analysis responses into a single string
        formatted_responses = ""
        for i, analysis in enumerate(analysis_responses):
            prompt = analysis.get("prompt", f"Analysis {i + 1}")
            result = analysis.get("result", "No result.")
            formatted_responses += f"--- Analysis for Prompt: {prompt} ---\n{result}\n\n"

        # Define the meta-analysis prompt
        meta_prompt_template = """
Given the following regulation text and a set of analyses performed on it, please provide a high-level summary.

Original Regulation Text:
---
{regulation_text}
---

Analyses:
---
{analysis_responses}
---

Based on the text and analyses, provide a JSON object with the following structure:
{{
  "recommended_action": "...",
  "goal_alignment": "...",
  "bullet_summary": ["...", "...", "..."]
}}

Instructions:
- For "recommended_action", choose one of: deletion, simplification, harmonization, modernization, enhancement.
- For "goal_alignment", choose one of: underachieves public policy goals, achieves, overachieves.
- For "bullet_summary", provide exactly three brief bullet points (under 10 words each) summarizing the key recommendations.
"""
        prompt = meta_prompt_template.format(
            regulation_text=regulation_text[:4000],  # Ensure text is truncated
            analysis_responses=formatted_responses
        )

        prompt_config = {
            "key": "meta_analysis",
            "prompt_config": {"messages": [{"role": "user", "content": prompt}]}
        }

        # Make the LLM call, expecting a JSON object
        response = llm_caller.get_responses_from_multiple_models(
            prompt_configs=[prompt_config],
            models=["gemini/gemini-2.5-flash"],
            response_format_type="json_object"
        )

        # Extract and return the parsed content
        parsed_content = response.get("gemini/gemini-2.5-flash", [{}])[0].get("parsed_content", {})
        if isinstance(parsed_content, dict) and "error" not in parsed_content:
            return parsed_content
        else:
            logger.warning(f"Meta-analysis failed or returned an error: {parsed_content}")
            return {
                "recommended_action": "error",
                "goal_alignment": "error",
                "bullet_summary": ["Failed to generate summary."]
            }

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
    def fetch_federal_register_data(self, start_date: str = "2025-07-01", end_date: str = "2025-07-31",
                                    agency: str = None) -> List[Dict[str, Any]]:
        """Fetch Federal Register documents published within the date range."""
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            params = {
                "fields[]": ["title", "full_text_xml_url", "agencies", "publication_date", "document_number"],
                "per_page": 1000,
                "publication_date_gte": start_date,
                "publication_date_lte": end_date,
                "order": "newest"
            }
            if self.api_key and self.api_key != "your_federal_register_api_key":
                params["api_key"] = self.api_key
            if agency:
                params["conditions[agencies][]"] = agency

            logger.debug(f"API query parameters: {params}")
            all_documents = []
            page = 1
            while True:
                params["page"] = page
                encoded_params = urllib.parse.urlencode(params, doseq=True)
                response = requests.get(f"{self.base_url}?{encoded_params}", timeout=self.request_timeout)
                response_data = response.json()
                logger.debug(
                    f"API response page {page} metadata: total_count={response_data.get('total_count', 'unknown')}, next_page_url={response_data.get('next_page_url', 'none')}")
                response.raise_for_status()
                documents = response_data.get("results", [])

                valid_documents = []
                for doc in documents:
                    doc_date = doc.get("publication_date", "")
                    try:
                        doc_dt = datetime.strptime(doc_date, "%Y-%m-%d").date()
                        if not (start_dt <= doc_dt <= end_dt):
                            continue
                    except ValueError:
                        continue
                    valid_documents.append(doc)

                all_documents.extend(valid_documents)

                if not response_data.get("next_page_url") or not documents:
                    break
                page += 1

            logger.info(
                f"Fetched {len(all_documents)} documents from Federal Register for {start_date} to {end_date}" + (
                    f" for agency: {agency}" if agency else ""))
            return all_documents
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Federal Register data: {str(e)}")
            return []

    def parse_xml_content(self, xml_url: str) -> str:
        """Parse XML content from a given URL."""
        try:
            logger.debug(f"Fetching XML from {xml_url}")
            response = requests.get(xml_url, timeout=self.request_timeout)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            text = " ".join(root.itertext()).strip()
            if not text:
                logger.warning(f"No text extracted from XML at {xml_url}")
            else:
                text = text[:4000]
            return text
        except (requests.RequestException, ET.ParseError) as e:
            logger.error(f"Error processing XML from {xml_url}: {str(e)}")
            return ""

    def ingest_regulation(self, reg_data: Dict[str, Any]) -> bool:
        """Store regulation data in the database."""
        try:
            query = """
                INSERT OR IGNORE INTO regulations (reg_number, title, text, effective_date, agency)
                VALUES (?, ?, ?, ?, ?)
            """
            params = (
                reg_data.get("document_number", ""),
                reg_data.get("title", ""),
                reg_data.get("text", ""),
                reg_data.get("publication_date", ""),
                reg_data.get("agency", "")
            )
            self.db.execute_query(query, params)
            return True
        except Exception as e:
            logger.error(f"Error ingesting regulation {reg_data.get('document_number', 'unknown')}: {str(e)}")
            return False

    def chunk_by_agency(self, documents: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Organize documents by agency."""
        agency_chunks = {}
        for doc in documents:
            display_agency = doc.get("agencies", [{}])[0].get("name", "Unknown")
            if display_agency not in agency_chunks:
                agency_chunks[display_agency] = []
            agency_chunks[display_agency].append(doc)
        return agency_chunks

    def analyze_regulation(self, reg_id: int, prompt_strategy_name: str = "DOGE Criteria") -> Dict[str, Any]:
        """Analyze a single regulation by ID using a specified prompt strategy."""
        try:
            query = "SELECT text FROM regulations WHERE id = ?"
            result = self.db.execute_query(query, (reg_id,))
            if not result:
                return {"error": "Regulation not found"}

            reg_text = result[0][0]
            prompts = self.prompt_strategies.get(prompt_strategy_name)
            if not prompts:
                return {"error": f"Prompt strategy '{prompt_strategy_name}' not found."}

            model_name = "gemini/gemini-2.5-flash"

            prompt_configs = []
            for i, prompt_template in enumerate(prompts):
                prompt = prompt_template.format(text=reg_text[:4000])
                prompt_configs.append({
                    "key": f"prompt_{i}",
                    "prompt_config": {"messages": [{"role": "user", "content": prompt}]}
                })

            responses = llm_caller.get_responses_from_multiple_models(
                prompt_configs=prompt_configs, models=[model_name], response_format_type="text"
            )

            analysis_results = []
            model_responses = responses.get(model_name, [])
            for i, prompt_template in enumerate(prompts):
                prompt_key = f"prompt_{i}"
                response_item = next((r for r in model_responses if r.get('prompt_key') == prompt_key), None)
                result_text = "Error: No response received."
                if response_item:
                    parsed_content = response_item.get("parsed_content")
                    if isinstance(parsed_content, dict) and "error" in parsed_content:
                        result_text = f"Error: {parsed_content.get('error')}"
                    else:
                        result_text = parsed_content
                analysis_results.append({
                    "prompt": prompt_template.split("\n")[0],
                    "result": result_text
                })

            # Perform meta-analysis on the results
            meta_analysis_result = self._get_meta_analysis(reg_text, analysis_results)

            # Return a structure consistent with the batch analysis
            return {
                "prompt_strategy_name": prompt_strategy_name,
                "analyses": analysis_results,
                "meta_analysis": meta_analysis_result
            }
        except Exception as e:
            logger.error(f"Analysis error for regulation {reg_id}: {str(e)}")
            return {"error": str(e)}

    def analyze_chunk(self, chunk: List[Dict[str, Any]], agency: str, prompts: List[str], prompt_strategy_name: str,
                      progress_callback=None, start_index=0, total_docs=0) -> List[Dict[str, Any]]:
        """Analyze a chunk of documents with a given list of prompts."""
        results = []
        model_name = "gemini/gemini-2.5-flash"

        for i, doc in enumerate(chunk):
            if self.llm_call_limit is not None and self.llm_calls_made >= self.llm_call_limit:
                logger.warning(f"LLM call limit ({self.llm_call_limit}) reached. Halting analysis for this chunk.")
                break

            current_index = start_index + i
            doc_id = doc.get("document_number", "unknown")

            if progress_callback:
                message = f"Analyzing document {current_index + 1}/{total_docs} ({doc_id})..."
                progress_callback(current_index + 1, total_docs, message)

            text = self.parse_xml_content(doc.get("full_text_xml_url", ""))
            if not text.strip():
                logger.warning(f"Skipping document {doc_id} due to empty text")
                continue

            # Step 1: Get individual prompt responses
            prompt_configs_for_doc = []
            for j, prompt_template in enumerate(prompts):
                prompt = prompt_template.format(text=text)
                prompt_configs_for_doc.append({
                    "key": f"prompt_{j}",
                    "prompt_config": {"messages": [{"role": "user", "content": prompt}]}
                })

            responses = llm_caller.get_responses_from_multiple_models(
                prompt_configs=prompt_configs_for_doc, models=[model_name], response_format_type="text"
            )
            self.llm_calls_made += len(prompt_configs_for_doc)

            analysis_results = []
            model_responses = responses.get(model_name, [])
            for j, prompt_template in enumerate(prompts):
                prompt_key = f"prompt_{j}"
                response_item = next((r for r in model_responses if r.get('prompt_key') == prompt_key), None)
                result_text = "Error: No response received."
                if response_item:
                    parsed_content = response_item.get("parsed_content")
                    if isinstance(parsed_content, dict) and "error" in parsed_content:
                        result_text = f"Error: {parsed_content.get('error')}"
                    else:
                        result_text = parsed_content
                analysis_results.append({
                    "prompt": prompt_template.split("\n")[0],
                    "result": result_text
                })

            # Step 2: Perform meta-analysis on the results
            if self.llm_call_limit is not None and self.llm_calls_made >= self.llm_call_limit:
                meta_analysis_result = {
                    "recommended_action": "limit_reached",
                    "goal_alignment": "limit_reached",
                    "bullet_summary": ["LLM limit reached before meta-analysis."]
                }
            else:
                meta_analysis_result = self._get_meta_analysis(text, analysis_results)
                self.llm_calls_made += 1  # Account for the meta-analysis call

            # Step 3: Store everything
            reg_data = {
                "document_number": doc_id,
                "title": doc.get("title", ""),
                "text": text,
                "publication_date": doc.get("publication_date", ""),
                "agency": agency
            }
            if self.ingest_regulation(reg_data):
                results.append({
                    "document_number": doc_id,
                    "title": doc.get("title", ""),
                    "agency": agency,
                    "prompt_strategy_name": prompt_strategy_name,
                    "analyses": analysis_results,
                    "meta_analysis": meta_analysis_result
                })
        return results

    def process_federal_register(self, start_date: str = "2025-07-01", end_date: str = "2025-07-31",
                                 agency: Optional[str] = None, doc_limit: Optional[int] = None,
                                 llm_call_limit: Optional[int] = None,
                                 prompt_strategy_name: str = "DOGE Criteria",
                                 progress_callback=None) -> Dict[str, Any]:
        """Main method to fetch, chunk, and analyze Federal Register data."""
        self.llm_calls_made = 0
        self.llm_call_limit = llm_call_limit

        prompts = self.prompt_strategies.get(prompt_strategy_name)
        if not prompts:
            return {"status": "error", "message": f"Prompt strategy '{prompt_strategy_name}' not found."}
        logger.info(f"Using prompt strategy: {prompt_strategy_name}")

        try:
            documents = self.fetch_federal_register_data(start_date, end_date, agency)
            if not documents:
                return {"status": "error", "message": "No documents fetched"}

            if doc_limit is not None and doc_limit > 0:
                logger.info(f"Limiting processing to the first {doc_limit} of {len(documents)} fetched documents.")
                documents = documents[:doc_limit]

            total_docs = len(documents)
            if progress_callback:
                progress_callback(0, total_docs, f"Fetched {total_docs} documents. Starting analysis...")

            agency_chunks = self.chunk_by_agency(documents)
            if not agency_chunks:
                logger.warning(f"No documents found for the specified criteria.")
                return {"status": "success", "results": []}

            all_results = []
            processed_docs_count = 0
            for chunk_agency, chunk in agency_chunks.items():
                logger.info(f"Processing {len(chunk)} documents for agency: {chunk_agency}")
                results = self.analyze_chunk(chunk, chunk_agency, prompts, prompt_strategy_name,
                                             progress_callback, processed_docs_count,
                                             total_docs)
                all_results.extend(results)
                processed_docs_count += len(results)

                # Check if the limit was hit and stop processing more chunks
                if self.llm_call_limit is not None and self.llm_calls_made >= self.llm_call_limit:
                    logger.warning(f"LLM call limit ({self.llm_call_limit}) reached. Halting further processing.")
                    break

            if progress_callback:
                progress_callback(total_docs, total_docs, "Ingestion complete!")
            return {"status": "success", "results": all_results}
        except Exception as e:
            logger.error(f"Error processing Federal Register data: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}
