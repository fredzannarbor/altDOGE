import requests
import xml.etree.ElementTree as ET
from src.database import Database
from src.litellm_fallback import LiteLLMFallback
from typing import Dict, Any, List, Tuple
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv
import logging
import backoff

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class IngestionManager:
    def __init__(self, db: Database, llm: LiteLLMFallback):
        self.db = db
        self.llm = llm
        self.api_key = os.getenv("FEDERAL_REGISTER_API_KEY")
        self.base_url = "https://www.federalregister.gov/api/v1/documents"
        self.chunk_size = 100  # Number of documents per chunk

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
    def fetch_federal_register_data(self, start_date: str = "2025-01-20") -> List[Dict[str, Any]]:
        """Fetch Federal Register documents published after the start date."""
        try:
            params = {
                "fields[]": ["title", "full_text_xml_url", "agencies", "publication_date", "document_number"],
                "per_page": 1000,
                "publication_date_gte": start_date,
                "order": "newest"
            }
            if self.api_key:
                params["api_key"] = self.api_key

            all_documents = []
            page = 1
            while True:
                params["page"] = page
                response = requests.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                documents = data.get("results", [])
                all_documents.extend(documents)

                if not data.get("next_page_url"):
                    break
                page += 1

            logger.info(f"Fetched {len(all_documents)} documents from Federal Register")
            return all_documents
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Federal Register data: {str(e)}")
            return []

    def parse_xml_content(self, xml_url: str) -> str:
        """Parse XML content from a given URL."""
        try:
            response = requests.get(xml_url)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            text_elements = root.findall(".//{http://www.w3.org/XML/1998/namespace}text")
            return " ".join([elem.text for elem in text_elements if elem.text])[:10000]  # Limit text size
        except (requests.exceptions.RequestException, ET.ParseError) as e:
            logger.error(f"Error parsing XML from {xml_url}: {str(e)}")
            return ""

    def ingest_regulation(self, reg_data: Dict[str, Any]) -> bool:
        """Store regulation data in the database."""
        try:
            query = """
                INSERT INTO regulations (reg_number, title, text, effective_date, agency)
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
        """Organize documents by agency, chunking large datasets."""
        agency_chunks = {}
        for doc in documents:
            agencies = [agency.get("name", "Unknown") for agency in doc.get("agencies", [])]
            agency_name = agencies[0] if agencies else "Unknown"

            if agency_name not in agency_chunks:
                agency_chunks[agency_name] = []
            agency_chunks[agency_name].append(doc)

            # Chunk if exceeding size limit
            if len(agency_chunks[agency_name]) > self.chunk_size:
                agency_chunks[f"{agency_name}_{len(agency_chunks[agency_name]) // self.chunk_size}"] = \
                    agency_chunks[agency_name][-self.chunk_size:]
                agency_chunks[agency_name] = agency_chunks[agency_name][:-self.chunk_size]

        return agency_chunks

    def define_alternative_prompts(self) -> List[str]:
        """Define alternative prompts for analysis."""
        return [
            "Analyze the following regulation text and categorize as Statutorily Required (SR), Not Statutorily Required (NSR), or Not Required but Agency Needs (NRAN). Provide a detailed justification citing statutory provisions if applicable:\n{text}",
            "Evaluate the following regulation for potential reform actions (deletion, simplification, harmonization, modernization). Suggest specific changes with justifications:\n{text}",
            "Identify any outdated terminology or processes in the following regulation and propose modernized alternatives:\n{text}",
            "Assess the clarity of the following regulation and suggest rephrasing to reduce ambiguity:\n{text}"
        ]

    def analyze_chunk(self, chunk: List[Dict[str, Any]], agency: str) -> List[Dict[str, Any]]:
        """Analyze a chunk of documents with alternative prompts."""
        results = []
        prompts = self.define_alternative_prompts()

        for doc in chunk:
            text = self.parse_xml_content(doc.get("full_text_xml_url", ""))
            if not text:
                continue

            doc_id = doc.get("document_number", "")
            analysis_results = []

            for prompt_template in prompts:
                prompt = prompt_template.format(text=text[:4000])  # Limit prompt size
                try:
                    result = self.llm.completion_with_fallback(prompt)
                    if result["status"] == "success":
                        analysis_results.append({
                            "prompt": prompt_template.split("\n")[0],
                            "result": result["response"]
                        })
                    else:
                        analysis_results.append({
                            "prompt": prompt_template.split("\n")[0],
                            "error": result["message"]
                        })
                except Exception as e:
                    logger.error(f"LLM analysis failed for document {doc_id}: {str(e)}")
                    analysis_results.append({
                        "prompt": prompt_template.split("\n")[0],
                        "error": str(e)
                    })

            # Store regulation in database
            reg_data = {
                "document_number": doc_id,
                "title": doc.get("title", ""),
                "text": text,
                "publication_date": doc.get("publication_date", ""),
                "agency": agency
            }
            self.ingest_regulation(reg_data)

            results.append({
                "document_number": doc_id,
                "agency": agency,
                "analyses": analysis_results
            })

        return results

    def process_federal_register(self, start_date: str = "2025-01-20") -> Dict[str, Any]:
        """Main method to fetch, chunk, and analyze Federal Register data."""
        try:
            # Fetch data
            documents = self.fetch_federal_register_data(start_date)
            if not documents:
                return {"status": "error", "message": "No documents fetched"}

            # Chunk by agency
            agency_chunks = self.chunk_by_agency(documents)

            # Analyze each chunk
            all_results = []
            for agency, chunk in agency_chunks.items():
                logger.info(f"Processing {len(chunk)} documents for agency: {agency}")
                results = self.analyze_chunk(chunk, agency)
                all_results.extend(results)

            return {"status": "success", "results": all_results}
        except Exception as e:
            logger.error(f"Error processing Federal Register data: {str(e)}")
            return {"status": "error", "message": str(e)}