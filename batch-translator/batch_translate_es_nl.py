import os
import sys
import re
import glob
import json
import time
import random
import shutil
import pandas as pd
from google import genai
from google.genai import types
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Initialize GenAI Client
client = genai.Client()

BASE_DIR = '/home/user/.agents/skills/batch-translator'
GLOSSARY_DIR = os.path.join(BASE_DIR, 'context')

# Helper loaders (loaded ONCE during initialization)
def load_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Failed to load file {filepath}: {e}")
        return ""

def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load json file {filepath}: {e}")
        return []

def load_glossary_for_lang(lang_name):
    lang_mapping = {
        'swedish': 'swedish_glossary.json',
        'sv': 'swedish_glossary.json',
        'french': 'french_glossary.json',
        'fr': 'french_glossary.json',
        'spanish': 'spanish_glossary.json',
        'es': 'spanish_glossary.json',
        'dutch': 'dutch_glossary.json',
        'nl': 'dutch_glossary.json',
        'german': 'german_glossary.json',
        'de': 'german_glossary.json'
    }
    key = str(lang_name).lower().strip()
    filename = lang_mapping.get(key)
    if not filename:
        possible_filename = f"{key}_glossary.json"
        if os.path.exists(os.path.join(GLOSSARY_DIR, possible_filename)):
            filename = possible_filename
            
    if filename:
        filepath = os.path.join(GLOSSARY_DIR, filename)
        if os.path.exists(filepath):
            return load_json(filepath)
    return {}

# Design Priority Rule: Filter out DNT terms that conflict with language glossary
def get_active_dnt(glossary_dict, dnt_list):
    glossary_keys = {str(k).lower().strip() for k in glossary_dict.keys()}
    return [term for term in dnt_list if str(term).lower().strip() not in glossary_keys]

# Pre-processing validation: skip non-translatable text
def is_translatable(text):
    if text is None or pd.isna(text):
        return False
    text_str = str(text).strip()
    if not text_str:
        return False
    # Skip URLs
    if re.match(r'^(https?://|ftp://|www\.)', text_str, re.IGNORECASE):
        return False
    # Skip strings marked translatable="false"
    if 'translatable="false"' in text_str or "translatable='false'" in text_str:
        return False
    # Skip if contains no letters at all
    if not any(c.isalpha() for c in text_str):
        return False
    # Skip if text is purely numbers/placeholders
    cleaned = re.sub(r'\{[^}]*\}', '', text_str)
    cleaned = re.sub(r'%\d*\$?[a-zA-Z]', '', cleaned)
    cleaned = re.sub(r'<[^>]*>', '', cleaned)
    if not any(c.isalpha() for c in cleaned):
        return False
    return True

# Post-processing validation: length scaling and hallucination checks
def validate_translation(original, translated):
    if not translated or translated.startswith("ERROR:"):
        return original
    orig_str = str(original).strip()
    trans_str = str(translated).strip()
    
    # Strip wrapping quotes if original was not quoted
    if (trans_str.startswith('"') and trans_str.endswith('"')) or (trans_str.startswith("'") and trans_str.endswith("'")):
        if not ((orig_str.startswith('"') and orig_str.endswith('"')) or (orig_str.startswith("'") and orig_str.endswith("'"))):
            trans_str = trans_str[1:-1].strip()
            
    orig_len = len(orig_str)
    trans_len = len(trans_str)
    
    # Check length scaling: discard if > 4x original and > 100 characters
    if orig_len > 10 and trans_len >= 4 * orig_len:
        return original
        
    # Check for hallucinated prompt/context text
    hallucination_indicators = [
        "style_guide", "style guide", "glossary", "do_not_translate", "translation:",
        "here is", "sure, here", "swedish translation", "spanish translation", "dutch translation",
        "Company & Core Business", "Digital Ecosystem"
    ]
    for indicator in hallucination_indicators:
        if indicator.lower() in trans_str.lower() and indicator.lower() not in orig_str.lower():
            return original
            
    return trans_str

# Robust LLM calling with exponential backoff
def call_gemini(prompt, system_instruction, max_attempts=8):
    for attempt in range(max_attempts):
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0
            )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=config
            )
            if response.text:
                return response.text.strip()
            return ""
        except Exception as e:
            if attempt == max_attempts - 1:
                return f"ERROR: {str(e)}"
            sleep_time = (2 ** attempt) * 1.5 + random.uniform(0.5, 1.5)
            if "429" in str(e) or "quota" in str(e).lower():
                sleep_time += 5
            time.sleep(sleep_time)
    return "ERROR: Max retries exceeded"

def main():
    # Context Loading: Read all context files ONCE during initialization
    style_guide = load_file(os.path.join(GLOSSARY_DIR, 'Translationsupport.md'))
    raw_dnt = load_json(os.path.join(GLOSSARY_DIR, 'do_not_translate.json'))
    
    # Load glossaries
    sv_glossary = load_glossary_for_lang("Swedish")
    es_glossary = load_glossary_for_lang("Spanish")
    nl_glossary = load_glossary_for_lang("Dutch")
    
    # Filter DNT per language according to Design Priority Rule
    sv_dnt = get_active_dnt(sv_glossary, raw_dnt)
    es_dnt = get_active_dnt(es_glossary, raw_dnt)
    nl_dnt = get_active_dnt(nl_glossary, raw_dnt)
    
    # Pre-build System Prompt: Pass 1 (Swedish Anchor)
    sys_prompt_anchor = f"""You are a professional localization expert for Roxtec.
Translate the given text in <source_english_text> from English into Swedish (Svenska) as the primary domain reference.

Follow these strict guidelines:
1. Preserve all placeholders like {{0}}, {{1}}, %s, %d, and HTML/XML tags or math symbols (<, >) exactly. Do not translate or alter them.
2. Glossary has highest priority: If a term is in the <glossary>, you MUST translate it according to that glossary.
3. Terms in <do_not_translate> must NOT be translated and must remain exactly as they appear in the source text, unless overridden by the glossary.
4. Respect the core style guide and phrasing guidelines. Use <developer_comment> only for contextual disambiguation; NEVER translate or output the developer comment.
5. Return ONLY the translated Swedish text for <source_english_text>. Do not return explanations, XML tags, markdown code fences, or style notes.

<style_guide>
{style_guide}
</style_guide>

<glossary>
{json.dumps(sv_glossary, ensure_ascii=False, indent=2)}
</glossary>

<do_not_translate>
{json.dumps(sv_dnt, ensure_ascii=False, indent=2)}
</do_not_translate>
"""

    # Pre-build System Prompt: Pass 2 (Spanish Target)
    sys_prompt_es = f"""You are a professional localization expert for Roxtec.
Translate the given English text in <source_english_text> into Spanish (Español).

Follow these strict guidelines:
1. Preserve all placeholders like {{0}}, {{1}}, %s, %d, and HTML/XML tags or math symbols (<, >) exactly.
2. Glossary priority: If a term is defined in <target_glossary_spanish>, you MUST use that translation. This has absolute highest priority.
3. Terms in <do_not_translate> must NOT be translated and must remain exactly as in English, unless overridden by the target glossary.
4. Semantic Triangulation: Use the Swedish anchor translation and <anchor_glossary_swedish> to disambiguate English terms and select the precise Roxtec domain concepts. Use <developer_comment> only for contextual disambiguation; NEVER translate or output the developer comment.
5. Respect the core style guide.
6. Return ONLY the translated Spanish text for <source_english_text>. No explanations, XML tags, markdown wrappers, or metadata.

<style_guide>
{style_guide}
</style_guide>

<anchor_glossary_swedish>
{json.dumps(sv_glossary, ensure_ascii=False, indent=2)}
</anchor_glossary_swedish>

<target_glossary_spanish>
{json.dumps(es_glossary, ensure_ascii=False, indent=2)}
</target_glossary_spanish>

<do_not_translate>
{json.dumps(es_dnt, ensure_ascii=False, indent=2)}
</do_not_translate>
"""

    # Pre-build System Prompt: Pass 2 (Dutch Target)
    sys_prompt_nl = f"""You are a professional localization expert for Roxtec.
Translate the given English text in <source_english_text> into Dutch (Nederlands).

Follow these strict guidelines:
1. Preserve all placeholders like {{0}}, {{1}}, %s, %d, and HTML/XML tags or math symbols (<, >) exactly.
2. Glossary priority: If a term is defined in <target_glossary_dutch>, you MUST use that translation. This has absolute highest priority.
3. Terms in <do_not_translate> must NOT be translated and must remain exactly as in English, unless overridden by the target glossary.
4. Semantic Triangulation: Use the Swedish anchor translation and <anchor_glossary_swedish> to disambiguate English terms and select the precise Roxtec domain concepts. Use <developer_comment> only for contextual disambiguation; NEVER translate or output the developer comment.
5. Respect the core style guide.
6. Return ONLY the translated Dutch text for <source_english_text>. No explanations, XML tags, markdown wrappers, or metadata.

<style_guide>
{style_guide}
</style_guide>

<anchor_glossary_swedish>
{json.dumps(sv_glossary, ensure_ascii=False, indent=2)}
</anchor_glossary_swedish>

<target_glossary_dutch>
{json.dumps(nl_glossary, ensure_ascii=False, indent=2)}
</target_glossary_dutch>

<do_not_translate>
{json.dumps(nl_dnt, ensure_ascii=False, indent=2)}
</do_not_translate>
"""

    # Locate target Excel file strictly from inside batch-translator directory unless explicit path given
    search_dir = sys.argv[1] if len(sys.argv) > 1 else BASE_DIR
    if os.path.isfile(search_dir):
        input_file = search_dir
    else:
        if not os.path.isdir(search_dir):
            search_dir = BASE_DIR
        excel_files = glob.glob(os.path.join(search_dir, '*.xlsx'))
        candidate_files = [
            f for f in excel_files
            if not f.endswith(('_completed.xlsx', '_output.xlsx', '_updated.xlsx', '_test.xlsx', '.backup', '.orig'))
        ]
        if not candidate_files:
            print(f"No input Excel file found in {search_dir}.")
            return
        input_file = max(candidate_files, key=os.path.getmtime)

    print(f"Loaded target Excel file: {input_file}")
    
    # Dynamically detect sheet name and header row (header=0 vs header=1)
    xl = pd.ExcelFile(input_file)
    orig_sheet_name = xl.sheet_names[0]
    df_check = pd.read_excel(input_file, sheet_name=orig_sheet_name, header=0, keep_default_na=False)
    if any(col in df_check.columns for col in ['ID', 'en', 'Master']):
        header_row = 0
        df = df_check
    else:
        header_row = 1
        df = pd.read_excel(input_file, sheet_name=orig_sheet_name, header=1, keep_default_na=False)

    total_rows = len(df)
    print(f"Total rows in dataset: {total_rows} (sheet='{orig_sheet_name}', header={header_row})")
    
    # Ensure source English is extracted from Master if 'en' is missing/empty
    if 'en' in df.columns and 'Master' in df.columns:
        df['en'] = df.apply(lambda r: r['en'] if str(r['en']).strip() != '' else r['Master'], axis=1)
    elif 'Master' in df.columns:
        df['en'] = df['Master']
        
    df['sv'] = ""
    df['sv'] = df['sv'].astype(object)
    if 'es' not in df.columns:
        df['es'] = ""
    df['es'] = df['es'].astype(object)
    if 'nl' not in df.columns:
        df['nl'] = ""
    df['nl'] = df['nl'].astype(object)
    df['en'] = df['en'].astype(object)

    # PASS 1: Swedish Anchor Translation (Concurrency + tqdm)
    print("\n--- Pass 1: Translating to Swedish Anchor (Domain Reference) ---")
    def process_anchor(idx, row):
        source_text = str(row['en']).strip() if str(row['en']).strip() else str(row.get('Master', '')).strip()
        comment_text = str(row.get('Comment', '')).strip()
        if is_translatable(source_text):
            prompt_content = f"""<source_english_text>
{source_text}
</source_english_text>

<developer_comment>
{comment_text}
</developer_comment>"""
            raw_trans = call_gemini(prompt=prompt_content, system_instruction=sys_prompt_anchor)
            sv_text = validate_translation(source_text, raw_trans)
        else:
            sv_text = source_text
        return idx, sv_text

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_anchor, idx, row): idx for idx, row in df.iterrows()}
        for future in tqdm(as_completed(futures), total=total_rows, desc="Translating Swedish Anchor", file=sys.stdout):
            try:
                idx, sv_text = future.result()
                df.at[idx, 'sv'] = sv_text
            except Exception as e:
                print(f"Exception at row {futures[future]}: {e}")

    # PASS 2: Downstream Target Languages (Spanish and Dutch) (Concurrency + tqdm)
    print("\n--- Pass 2: Translating to Target Languages (es, nl) via Semantic Triangulation ---")
    def process_downstream(idx, row):
        source_text = str(row['en']).strip() if str(row['en']).strip() else str(row.get('Master', '')).strip()
        comment_text = str(row.get('Comment', '')).strip()
        sv_text = str(row['sv']).strip()
        
        if is_translatable(source_text):
            prompt_content = f"""<source_english_text>
{source_text}
</source_english_text>

<anchor_swedish_translation>
{sv_text}
</anchor_swedish_translation>

<developer_comment>
{comment_text}
</developer_comment>
"""
            # Spanish translation
            raw_es = call_gemini(prompt=prompt_content, system_instruction=sys_prompt_es)
            es_text = validate_translation(source_text, raw_es)
            
            # Dutch translation
            raw_nl = call_gemini(prompt=prompt_content, system_instruction=sys_prompt_nl)
            nl_text = validate_translation(source_text, raw_nl)
        else:
            es_text = source_text
            nl_text = source_text
            
        return idx, es_text, nl_text

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_downstream, idx, row): idx for idx, row in df.iterrows()}
        for future in tqdm(as_completed(futures), total=total_rows, desc="Translating Downstream (ES & NL)", file=sys.stdout):
            try:
                idx, es_text, nl_text = future.result()
                df.at[idx, 'es'] = es_text
                df.at[idx, 'nl'] = nl_text
            except Exception as e:
                print(f"Exception at row {futures[future]}: {e}")

    # Prepare export DataFrame (including Swedish anchor column)
    export_cols = [c for c in ['ID', 'Comment', 'Master', 'en', 'es', 'nl', 'sv'] if c in df.columns]
    final_df = df[export_cols].copy()
    
    # Save a backup of the original if not already saved
    backup_file = input_file + '.orig'
    if not os.path.exists(backup_file):
        shutil.copyfile(input_file, backup_file)
        print(f"Created backup of original file: {backup_file}")

    # Update input file in place (preserving original sheet_name and header_row offset)
    with pd.ExcelWriter(input_file) as writer:
        final_df.to_excel(writer, sheet_name=orig_sheet_name, startrow=header_row, index=False)
    print(f"Successfully updated original file: {input_file}")

    # Also save standard completed export files
    completed_file = input_file.replace('.xlsx', '_completed.xlsx')
    with pd.ExcelWriter(completed_file) as writer:
        final_df.to_excel(writer, sheet_name=orig_sheet_name, index=False)
    print(f"Saved completed export: {completed_file}")

    alt_completed = os.path.join(BASE_DIR, 'translation_en_es_nl_completed.xlsx')
    with pd.ExcelWriter(alt_completed) as writer:
        final_df.to_excel(writer, sheet_name='Translation', index=False)
    print(f"Saved completed export: {alt_completed}")

if __name__ == '__main__':
    main()
