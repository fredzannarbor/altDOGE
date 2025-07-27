# /Users/fred/my-organizations/nimble/repos/codexes-factory/src/codexes/modules/builders/llm_get_book_data.py
import logging
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import time

from dotenv import load_dotenv

load_dotenv()

from codexes.core import llm_caller, prompt_manager

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(name)s.%(funcName)s:%(lineno)d - %(message)s')
logger = logging.getLogger(__name__)


def reprompt_and_update(
    book_data: Dict[str, Any],
    prompt_key: str,
    prompt_template_file: str,
    model_name: str,
    per_model_params: Dict
) -> Optional[Dict[str, Any]]:
    """
    Reprompts with a specific key and returns the updated data.
    """
    title = book_data.get("title", "Untitled")
    description = book_data.get('description', 'No description provided')
    quotes = book_data.get("quotes", [])

    quotes_text = ""
    if quotes:
        quotes_text = "\n\nQuotations in this book:\n"
        for i, quote in enumerate(quotes, 1):
            q_text = quote.get("quote", "")
            q_author = quote.get("author", "Unknown")
            q_source = quote.get("source", "Unknown")
            quotes_text += f"{i}. \"{q_text}\" - {q_author}, {q_source}\n"

    book_content = f"Title: {title}\n\nDescription: {description}{quotes_text}"

    substitutions = {
        "book_content": book_content,
        "title": title,
        "topic": title,
        "stream": book_data.get("stream", "General"),
        "description": description,
        "quotes_per_book": len(quotes),
        "special_requests": book_data.get("special_requests", ""),
        "recommended_sources": book_data.get("recommended_sources", "")
    }

    formatted_prompts = prompt_manager.load_and_prepare_prompts(
        prompt_file_path=prompt_template_file,
        prompt_keys=[prompt_key],
        substitutions=substitutions
    )

    if not formatted_prompts:
        logger.error(f"Could not load or prepare the prompt for key '{prompt_key}' for book '{title}'.")
        return None

    responses = llm_caller.get_responses_from_multiple_models(
        prompt_configs=formatted_prompts, models=[model_name],
        response_format_type="json_object", per_model_params=per_model_params
    )

    for model_name, model_responses in responses.items():
        for response_item in model_responses:
            if response_item.get('prompt_key') == prompt_key:
                return response_item.get('parsed_content')

    return None


def process_book(
        book_data: Dict[str, Any],
        prompt_template_file: str,
        model_name: str,
        per_model_params: Dict,
        raw_output_dir: Path,
        safe_basename: str,
        prompt_keys: List[str],
        catalog_only: bool = False,
        build_dir: Optional[Path] = None,
        save_responses: bool = False
) -> tuple[Optional[Dict[str, Any]], Dict[str, int]]:
    """
    Processes a single book entry, generates all required data, and returns stats.
    Saves raw LLM responses to the specified directory.
    """
    title = book_data.get("title", f"Title_TBD_{time.time()}")
    stream = book_data.get("stream", "Stream_TBD")
    description = book_data.get('description', 'Expand topic logically into related concepts.')
    logging.info(f"Processing book: '{title}' in stream: '{stream}'")

    if catalog_only:
        logger.info("Running in catalog-only mode. Using a reduced set of prompts.")
        prompt_keys = [k for k in prompt_keys if "storefront" in k or "bibliographic" in k or "back_cover" in k]

    quotes = book_data.get("quotes", [])
    quotes_text = ""
    if quotes:
        quotes_text = "\n\nQuotations in this book:\n"
        for i, quote in enumerate(quotes, 1):
            q_text = quote.get("quote", "")
            q_author = quote.get("author", "Unknown")
            q_source = quote.get("source", "Unknown")
            quotes_text += f"{i}. \"{q_text}\" - {q_author}, {q_source}\n"

    book_content = f"Title: {title}\n\nDescription: {description}{quotes_text}"
    
    substitutions = {
        "book_content": book_content,
        "topic": title,
        "stream": stream,
        "description": description,
        "quotes_per_book": book_data.get("quotes_per_book", 90),
        "special_requests": book_data.get("special_requests", ""),
        "recommended_sources": book_data.get("recommended_sources", "")
    }
    
    formatted_prompts = prompt_manager.load_and_prepare_prompts(
        prompt_file_path=prompt_template_file,
        prompt_keys=prompt_keys,
        substitutions=substitutions
    )

    if not formatted_prompts:
        logging.error(f"Could not load or prepare any prompts for book '{title}'. Skipping.")
        return None, {"prompts_successful": 0, "quotes_found": 0}

    responses = llm_caller.get_responses_from_multiple_models(
        prompt_configs=formatted_prompts, models=[model_name],
        response_format_type="json_object", per_model_params=per_model_params
    )
    
    # Save LLM responses to JSON if requested
    if save_responses and build_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for model_name, model_responses in responses.items():
            for response_item in model_responses:
                prompt_key = response_item.get('prompt_key', 'unknown')
                prompt = response_item.get('prompt', '')
                content = response_item.get('content', {})
                
                # Save response to JSON file
                response_data = {
                    "timestamp": timestamp,
                    "model": model_name,
                    "prompt_key": prompt_key,
                    "prompt": prompt,
                    "response": content
                }
                
                filename = f"{safe_basename}_{prompt_key}_{timestamp}.json"
                response_file = build_dir / filename
                
                with open(response_file, 'w', encoding='utf-8') as f:
                    json.dump(response_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"✅ Saved LLM response for {prompt_key} to {response_file}")

    final_book_json = {
        "title": title, "stream": stream, "description": description,
        "schedule_month_year": book_data.get("schedule_month_year", "Unknown"),
        "subtitle": "", "author": "AI Lab for Book-Lovers", "publisher": "Nimble Books LLC",
        "imprint": "xynapse traces", "publication_date": datetime.now().strftime('%Y-%m-%d'),
        "language": "English", "bisac_codes": "", "series_name": "", "series_number": "",
        "keywords": "", "storefront_title_en": title, "storefront_author_en": "AI Lab for Book-Lovers",
        "storefront_description_en": description, "storefront_title_ko": "", "storefront_author_ko": "",
        "storefront_description_ko": "", "storefront_publishers_note_en": "", "storefront_publishers_note_ko": "",
        "table_of_contents": "", "quotes": [], "custom_transcription_note": "",
        "mnemonics": "", "mnemonics_tex": "", "bibliography": "", "isbn13": "", "back_cover_text": "", "formatted_prompts": formatted_prompts
    }

    if catalog_only:
        final_book_json['page_count'] = 216
        final_book_json['author'] = "AI Lab for Book-Lovers"
        final_book_json['imprint'] = "xynapse traces"

    successful_prompts = 0
    final_book_json['responses'] = responses
    for model_name, model_responses in responses.items():
        for response_item in model_responses:
            prompt_key = response_item.get('prompt_key', 'unknown_prompt')
            raw_content = response_item.get('raw_content', '')
            parsed_content = response_item.get('parsed_content')

            try:
                raw_filename = f"{safe_basename}_{prompt_key}.txt"
                (raw_output_dir / raw_filename).write_text(raw_content, encoding='utf-8')
            except Exception as e:
                logger.error(f"Failed to write raw response for {prompt_key}: {e}")

            if not parsed_content or (isinstance(parsed_content, dict) and 'error' in parsed_content):
                logger.warning(f"LLM returned an error or invalid content for prompt '{prompt_key}': {parsed_content}")
                continue

            successful_prompts += 1

            def process_dict(data_dict: Dict):
                if not isinstance(data_dict, dict): return
                for key, value in data_dict.items():
                    if value is not None:
                        if key in final_book_json and isinstance(final_book_json[key], list) and isinstance(value,
                                                                                                            list):
                            final_book_json[key].extend(value)
                        elif key in final_book_json:
                            final_book_json[key] = value

            if isinstance(parsed_content, dict):
                process_dict(parsed_content)
            elif isinstance(parsed_content, list):
                for item in parsed_content:
                    process_dict(item)
            else:
                logger.warning(f"Unexpected content type '{type(parsed_content)}' for prompt '{prompt_key}'.")

    # --- Final Validation Step ---
    # Validate and correct the publication_date
    try:
        datetime.strptime(str(final_book_json.get('publication_date')), '%Y-%m-%d')
    except (ValueError, TypeError):
        logger.warning(f"Invalid or missing publication_date '{final_book_json.get('publication_date')}'. Replacing with current date.")
        final_book_json['publication_date'] = datetime.now().strftime('%Y-%m-%d')

    llm_stats = {
        "prompts_successful": successful_prompts,
        "quotes_found": len(final_book_json.get("quotes", []))
    }

    return final_book_json, llm_stats