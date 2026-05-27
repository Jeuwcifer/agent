---
name: batch-translator
description: Efficiently translates tabular string data (e.g., from Excel files) concurrently using LLMs. Prevents translation drift via term glossaries, preserves internal placeholders/tags, and utilizes contextual files. Triggers on requests like "translate this file", "batch translate", "run the translation script", or when asked to localize tabular data.
---

# Batch Translator Skill

When the user asks to translate strings, localize an application, or run a translation batch job, follow these guidelines.

## Architecture & Principles
1. **Never use sequential loops for network calls**: All LLM API calls must be parallelized (e.g., via `ThreadPoolExecutor`).
2. **Visual Feedback & Progress Tracking**: Show visual feedback when executing concurrent tasks. Always wrap `as_completed(futures)` with a `tqdm` progress bar to display real-time execution progress, ETA, and throughput on standard output.
3. **Batch Context**: Never repeatedly read context documents (DOCX) or glossaries per row. Read them once during initialization, convert to a prompt string, and pass to worker threads.
4. **Data Integrity & Validation**: 
   - Avoid raw cell-by-cell writes with libraries like `openpyxl`. Use `pandas` or proper XML parsing (`xml.etree.ElementTree`).
   - Implement strict pre-processing rules: Skip translation for URLs, strings marked as `translatable="false"`, empty strings, and strings containing only placeholders/numbers.
   - Implement strict post-processing validation: Compare the length of the generated translation to the original source. If the AI hallucinates contexts/style-guides (e.g., response length is 4x the original or contains known style guide text), automatically discard it and fallback to the original text.
5. **Resiliency**: Implement basic exception handling in threads so a single failing row returns an error string instead of crashing the batch.
6. **Semantic Triangulation (Anchor Language & Anchor Glossary)**: To prevent disambiguation errors and translation drift, employ a two-pass system:
   - Translate the source into the primary domain language (Swedish) first.
   - For all subsequent target languages, pass the source text, the generated Swedish anchor translation, and **both** the target glossary (if available) and the **Swedish anchor glossary** (as a universal semantic dictionary to map ambiguous English terms to precise Swedish domain concepts). Structurally isolate these in separate XML blocks (`<anchor_glossary_swedish>` and `<target_glossary_{lang}>`) inside the prompt to prevent lexical bleeding.

## Required Context Inputs
When requested to translate a file, ensure you have:
1. **Source File**: The target tabular data (e.g., Excel or CSV). **Strict Search Location Constraint**: You must ONLY search for, locate, or load source/Excel files from inside the `batch-translator` skill directory (`/home/user/.agents/skills/batch-translator/`). Never scan external directories, user home, or other workspace folders unless explicitly given a specific absolute path by the user.
2. **Target Languages**: What languages to translate into.
3. **Authentication**: Verify you have access to API keys (e.g., `GOOGLE_APPLICATION_CREDENTIALS` or a local key config file) based on the LLM being used.
4. **Context Files**: Reference the standard context files located in `context/`:
   - `context/swedish_glossary.json`: The standard Swedish terminology mapping.
   - `context/french_glossary.json`: The standard French terminology mapping.
   - `context/Translationsupport.md`: The core style guide and phrasing document.
   - `context/do_not_translate.json`: A list of terms (e.g., product names, system variables) that must remain exactly as they appear in the source text and never be translated.
     *Design Priority Rule*: If a term is defined in a language-specific glossary, it MUST be translated according to that glossary. This has the absolute highest priority and overrides `do_not_translate.json`. Terms in `do_not_translate.json` should be programmatically filtered out of the active "do not translate" list for any target language where they conflict with that language's glossary.

   *Note: Code implementations must dynamically load the correct glossary based on the target language (e.g., searching for `context/{language}_glossary.json` or mapping language names to glossary files) rather than hardcoding a single language glossary for all translations.*

## Workflow Example
1. Preprocess: Find strings to exclude, convert to placeholders. Read `do_not_translate.json` and ensure those terms are injected into the system prompt as immutable strings.
2. Initialize LLM Client.
3. Load DataFrame and parse context documents once.
4. Pass 1 (Anchor): Spin up concurrent threads to translate the source text into the primary anchor language (e.g., Swedish).
5. Pass 2 (Downstream): Spin up concurrent threads for remaining target languages, injecting both the source text and the anchor translation into the prompt.
6. Postprocess: Restore placeholders and validate length/hallucinations.
7. Export the finalized DataFrame.

## Standard Code Blueprint (Boilerplate)
Every new or modified translation script written by this skill MUST conform to the following concurrency and visual progress bar structure:

```python
import pandas as pd
from google import genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from time import sleep

client = genai.Client()

def process_row(idx, row):
    # Concurrency worker logic here
    # ...
    return idx, translated_text

def main():
    df = pd.read_excel('input_file.xlsx')
    total_rows = len(df)
    
    # ALWAYS use ThreadPoolExecutor + tqdm for visual progress tracking on stdout
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_row, idx, row): idx for idx, row in df.iterrows()}
        
        for future in tqdm(as_completed(futures), total=total_rows, desc="Translating Batch"):
            idx, result = future.result()
            df.at[idx, 'target_col'] = result
```
