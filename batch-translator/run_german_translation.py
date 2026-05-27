import os
import re
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from tqdm import tqdm
from google import genai
from google.genai import types

# Constants
BASE_DIR = '/home/user/.agents/skills/batch-translator'
INPUT_FILE = os.path.join(BASE_DIR, 'translation_en_es_nl-20260520T063532Z.xlsx')
OUTPUT_FILE = os.path.join(BASE_DIR, 'translation_en_es_nl_de-20260520.xlsx')
CHECKPOINT_FILE = os.path.join(BASE_DIR, 'checkpoint_translations.jsonl')

client = genai.Client()

# Load Context Files
with open(os.path.join(BASE_DIR, 'context/Translationsupport.md'), 'r', encoding='utf-8') as f:
    style_guide = f.read()

with open(os.path.join(BASE_DIR, 'context/do_not_translate.json'), 'r', encoding='utf-8') as f:
    do_not_translate_raw = json.load(f)

with open(os.path.join(BASE_DIR, 'context/swedish_glossary.json'), 'r', encoding='utf-8') as f:
    swedish_glossary = json.load(f)

# Design Priority Rule: Filter out do-not-translate terms that conflict with glossary
def get_active_do_not_translate(glossary_dict, dnt_list):
    active = []
    for term in dnt_list:
        conflict = False
        for key in glossary_dict.keys():
            if re.search(r'\b' + re.escape(term) + r'\b', key, re.IGNORECASE):
                conflict = True
                break
        if not conflict:
            active.append(term)
    return active

active_dnt_sv = get_active_do_not_translate(swedish_glossary, do_not_translate_raw)
active_dnt_de = do_not_translate_raw  # No German glossary, so no conflicts

# Check if a row should be skipped (URLs, only placeholders/numbers, etc.)
def should_skip(text):
    if not isinstance(text, str):
        return True
    text_stripped = text.strip()
    if not text_stripped:
        return True
    
    # Skip URLs
    if re.match(r'^(https?://|ftp://|www\.)', text_stripped, re.IGNORECASE):
        return True
    
    # Check if marked translatable="false"
    if 'translatable="false"' in text or "translatable='false'" in text:
        return True
    
    # If contains absolutely no letters, skip
    if not any(c.isalpha() for c in text_stripped):
        return True
        
    # Skip if only placeholders/numbers/punctuation remain after removing placeholders
    cleaned = re.sub(r'\{[^}]*\}', '', text_stripped)
    cleaned = re.sub(r'%[a-zA-Z]', '', cleaned)
    cleaned = re.sub(r'<[^>]*>', '', cleaned)  # HTML tags
    if not any(c.isalpha() for c in cleaned):
        return True
        
    return False

# Post-processing validation
def validate_translation(original, translated):
    if not isinstance(original, str) or not isinstance(translated, str):
        return True
    
    orig_len = len(original)
    trans_len = len(translated)
    
    # Check if length is 4x or more
    if orig_len > 10 and trans_len >= 4 * orig_len:
        return False
            
    # Check for hallucinated instructions/context
    hallucination_indicators = [
        "style_guide", "style guide", "glossary", "do_not_translate", "translation:", "translated:",
        "here is", "sure, here", "the swedish translation", "the german translation"
    ]
    for indicator in hallucination_indicators:
        if indicator in translated.lower() and indicator not in original.lower():
            return False
            
    return True

# Call Gemini API with robust retry and exponential backoff
def call_gemini(prompt, system_instruction, max_attempts=8):
    for attempt in range(max_attempts):
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0, # Keep translations deterministic and precise
            )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=config
            )
            text = response.text
            if text:
                return text.strip()
            return ""
        except Exception as e:
            if attempt == max_attempts - 1:
                return f"ERROR: {str(e)}"
            sleep_time = (2 ** attempt) * 2 + random.uniform(0, 1)
            if "429" in str(e):
                sleep_time += 5
            time.sleep(sleep_time)
    return "ERROR: Max retries exceeded"

# Translate single row (Two-pass)
def process_row(idx, row_dict):
    en_text = row_dict['en']
    
    if should_skip(en_text):
        return idx, en_text, en_text
    
    # Pass 1: Swedish Anchor
    sys_prompt_sv = f"""You are a professional localization expert for Roxtec.
Translate the given English text into Swedish (Svenska) as the primary domain language.

Follow these strict guidelines:
1. Preserve all placeholders like {{0}}, {{1}}, %s, %d, or HTML/XML tags exactly. Do not translate or modify them.
2. Respect the Swedish terminology glossary below. This has the highest priority.
3. Respect the core style guide and phrasing guidelines.
4. Do not translate terms in the <do_not_translate> list below. Keep them exactly as in English.
5. Return ONLY the translated Swedish text. Do not include any explanations, markdown code blocks, or extra words.

<style_guide>
{style_guide}
</style_guide>

<glossary>
{json.dumps(swedish_glossary, ensure_ascii=False, indent=2)}
</glossary>

<do_not_translate>
{json.dumps(active_dnt_sv, ensure_ascii=False, indent=2)}
</do_not_translate>
"""
    sv_trans = call_gemini(prompt=en_text, system_instruction=sys_prompt_sv)
    
    # Post-process validation for Swedish
    if sv_trans.startswith("ERROR:") or not validate_translation(en_text, sv_trans):
        sv_trans = en_text
        
    # Pass 2: German Target (Semantic Triangulation)
    sys_prompt_de = f"""You are a professional localization expert for Roxtec.
Translate the given English text into German (Deutsch).

You are provided with:
1. The English source text.
2. The Swedish anchor translation (the primary domain reference) to resolve ambiguous English terms.
3. The Swedish anchor glossary to map Swedish domain concepts.
4. The list of terms that must not be translated.

Follow these strict guidelines:
1. Preserve all placeholders like {{0}}, {{1}}, %s, %d, or HTML/XML tags exactly. Do not translate or modify them.
2. Use the Swedish anchor translation and Swedish anchor glossary to disambiguate the English terminology and ensure correct professional terminology in the German translation.
3. Respect the core style guide and phrasing guidelines.
4. Do not translate terms in the <do_not_translate> list below. Keep them exactly as in English.
5. Return ONLY the translated German text. Do not include any explanations, markdown code blocks, or extra words.

<style_guide>
{style_guide}
</style_guide>

<anchor_glossary_swedish>
{json.dumps(swedish_glossary, ensure_ascii=False, indent=2)}
</anchor_glossary_swedish>

<target_glossary_german>
{{}}
</target_glossary_german>

<do_not_translate>
{json.dumps(active_dnt_de, ensure_ascii=False, indent=2)}
</do_not_translate>
"""
    
    prompt_de = f"""<source_english_text>
{en_text}
</source_english_text>

<anchor_swedish_translation>
{sv_trans}
</anchor_swedish_translation>
"""
    
    de_trans = call_gemini(prompt=prompt_de, system_instruction=sys_prompt_de)
    
    # Post-process validation for German
    if de_trans.startswith("ERROR:") or not validate_translation(en_text, de_trans):
        de_trans = en_text
        
    return idx, sv_trans, de_trans

def main():
    print("Reading input Excel file...")
    df = pd.read_excel(INPUT_FILE, header=1)
    
    # Initialize translation columns
    df['sv'] = ""
    df['de'] = ""
    
    # Load checkpoint if exists
    checkpoint = {}
    if os.path.exists(CHECKPOINT_FILE):
        print(f"Resuming from checkpoint: {CHECKPOINT_FILE}")
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                checkpoint[int(data['idx'])] = (data['sv'], data['de'])
        print(f"Loaded {len(checkpoint)} translated rows from checkpoint.")
    
    # Apply existing checkpoint translations
    for idx, (sv, de) in checkpoint.items():
        if idx in df.index:
            df.at[idx, 'sv'] = sv
            df.at[idx, 'de'] = de
            
    # Identify rows that still need translation
    pending_rows = [
        (idx, row.to_dict())
        for idx, row in df.iterrows()
        if idx not in checkpoint
    ]
    
    limit_test = int(os.environ.get('LIMIT_TEST', 0))
    if limit_test > 0:
        print(f"TEST MODE: Limiting translation to first {limit_test} pending rows.")
        pending_rows = pending_rows[:limit_test]
        
    total_pending = len(pending_rows)
    print(f"Total rows: {len(df)}. Pending: {total_pending}.")
    
    if total_pending > 0:
        # Save checkpoints immediately inside progress loop
        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = {
                executor.submit(process_row, idx, row_dict): idx
                for idx, row_dict in pending_rows
            }
            
            with open(CHECKPOINT_FILE, 'a', encoding='utf-8') as cf:
                for future in tqdm(as_completed(futures), total=total_pending, desc="Translating (DE)"):
                    try:
                        idx, sv, de = future.result()
                        df.at[idx, 'sv'] = sv
                        df.at[idx, 'de'] = de
                        
                        # Write to checkpoint file
                        cf.write(json.dumps({'idx': idx, 'sv': sv, 'de': de}, ensure_ascii=False) + '\n')
                        cf.flush()
                    except Exception as e:
                        print(f"Exception in worker thread for index {futures[future]}: {e}")
                        
    # Ensure correct headers in output: we want ['ID', 'Comment', 'Master', 'en', 'es', 'nl', 'de']
    output_cols = ['ID', 'Comment', 'Master', 'en', 'es', 'nl', 'de']
    final_df = df[output_cols].copy()
    
    print(f"Saving finalized translations to {OUTPUT_FILE}...")
    final_df.to_excel(OUTPUT_FILE, index=False)
    print("Translation completed successfully!")

if __name__ == '__main__':
    main()
