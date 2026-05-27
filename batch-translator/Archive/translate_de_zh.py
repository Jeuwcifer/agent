import os
import re
import json
import pandas as pd
from google import genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep
from tqdm import tqdm

# Ensure API key is configured
if "GEMINI_API_KEY" not in os.environ:
    # Use fallback or throw error
    raise ValueError("GEMINI_API_KEY environment variable is required.")

client = genai.Client()

# Load Context and Glossaries
BASE_DIR = '/home/user/.agents/skills/batch-translator'
with open(f'{BASE_DIR}/context/Translationsupport.md', 'r') as f:
    style = f.read()
with open(f'{BASE_DIR}/context/do_not_translate.json', 'r') as f:
    dnt_list = json.load(f)

anchor_prompt_template = """You are a professional localization expert for Roxtec.
Translate the given text from English into Swedish (Anchor Language).
Preserve any placeholders like {{0}}, {{1}}, %s, or HTML tags.

CRITICAL INSTRUCTION:
1. If a term is defined in the target language glossary, it MUST be translated according to the glossary. This has the absolute highest priority.
2. If a term is in the list below, and is NOT overridden by the glossary, it MUST NOT be translated and must remain exactly as it appears:
{dnt_str}

Reference contexts for terminology and style constraints:
<glossary>
{glossary}
</glossary>
<style_guide>
{style}
</style_guide>

Return strictly the translated Swedish text, nothing else. No markdown wrappers or explanations.
"""

downstream_prompt_template = """You are a professional localization expert for Roxtec.
Translate the given English text into {target_lang}.
Preserve any placeholders like {{0}}, {{1}}, %s, or HTML tags.

CRITICAL INSTRUCTION:
1. If a term is defined in the target language glossary (e.g., <target_glossary_*>), it MUST be translated according to the glossary. This has the absolute highest priority.
2. If a term is in the list below, and is NOT overridden by the glossary, it MUST NOT be translated and must remain exactly as it appears:
{dnt_str}

Reference contexts for terminology and style constraints:

<anchor_glossary_swedish>
Use this primary Swedish glossary to disambiguate English terms (since Swedish is the core domain language of Roxtec):
{anchor_glossary}
</anchor_glossary_swedish>

<target_glossary_{target_lang_lower}>
Use this target glossary for the final translations into {target_lang} if terms are present:
{target_glossary}
</target_glossary_{target_lang_lower}>

<style_guide>
{style}
</style_guide>

To help with disambiguation, here is the English source and its Swedish translation:
English: {en_text}
Swedish: {anchor_text}

Return strictly the {target_lang} translated text for the English source. Do not return any explanations, markdown, or the style guide.
"""

GLOSSARY_DIR = f'{BASE_DIR}/context'

def load_glossary_for_lang(lang_name):
    lang_mapping = {
        'swedish': 'swedish_glossary.json',
        'sv': 'swedish_glossary.json',
        'german': 'german_glossary.json',
        'de': 'german_glossary.json',
        'chinese': 'chinese_glossary.json',
        'zh': 'chinese_glossary.json'
    }
    key = str(lang_name).lower().strip()
    filename = lang_mapping.get(key)
    if not filename:
        possible_filename = f"{key}_glossary.json"
        if os.path.exists(os.path.join(GLOSSARY_DIR, possible_filename)):
            filename = possible_filename
            
    if filename:
        filepath = os.path.join(GLOSSARY_DIR, filename)
        try:
            with open(filepath, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Failed to load glossary file {filepath}: {e}")
    return ""

def get_filtered_dnt_list(target_lang):
    filtered_dnt = list(dnt_list)
    lang_mapping = {
        'swedish': 'swedish_glossary.json',
        'sv': 'swedish_glossary.json',
        'german': 'german_glossary.json',
        'de': 'german_glossary.json',
        'chinese': 'chinese_glossary.json',
        'zh': 'chinese_glossary.json'
    }
    key = str(target_lang).lower().strip()
    filename = lang_mapping.get(key)
    if not filename:
        possible_filename = f"{key}_glossary.json"
        if os.path.exists(os.path.join(GLOSSARY_DIR, possible_filename)):
            filename = possible_filename
            
    if filename:
        filepath = os.path.join(GLOSSARY_DIR, filename)
        try:
            with open(filepath, 'r') as f:
                glossary_dict = json.load(f)
                glossary_keys = {str(k).lower().strip() for k in glossary_dict.keys()}
                filtered_dnt = [term for term in filtered_dnt if str(term).lower().strip() not in glossary_keys]
        except Exception as e:
            pass
    return filtered_dnt

def generate_with_retry(prompt):
    for attempt in range(8):
        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            err_msg = str(e)
            if '429' in err_msg or 'Quota' in err_msg or 'exhausted' in err_msg.lower():
                sleep((attempt + 1) * 5)
            else:
                sleep(2)
    return "ERROR: Max retries exceeded"

def is_translatable(text):
    if pd.isna(text) or not str(text).strip():
        return False
    text = str(text).strip()
    if text.startswith('http://') or text.startswith('https://'):
        return False
    if not re.search('[a-zA-Z]', text):
        return False
    return True

def validate_translation(original, translated):
    if not translated or translated.startswith("ERROR:"):
        return original
        
    original_len = len(str(original))
    if len(translated) > max(original_len * 4, 100):
        if "Roxtec" in translated or "Company & Core Business" in translated:
            return original
        if len(translated) > 300 and original_len < 50:
            return original
            
    if translated.startswith('"') and translated.endswith('"') and not str(original).startswith('"'):
        translated = translated[1:-1]
        
    return translated

def translate_anchor(text, target_lang="Swedish"):
    glossary = load_glossary_for_lang(target_lang)
    filtered_dnt = get_filtered_dnt_list(target_lang)
    filtered_dnt_str = ", ".join(filtered_dnt)
    sys_prompt = anchor_prompt_template.format(target_lang=target_lang, glossary=glossary, style=style, dnt_str=filtered_dnt_str)
    prompt = f"{sys_prompt}\n\nText to translate:\n<text>\n{text}\n</text>"
    raw_translation = generate_with_retry(prompt)
    return validate_translation(str(text), raw_translation)

def translate_downstream(en_text, anchor_text, target_lang):
    anchor_glossary = load_glossary_for_lang("Swedish")
    target_glossary = load_glossary_for_lang(target_lang)
    filtered_dnt = get_filtered_dnt_list(target_lang)
    filtered_dnt_str = ", ".join(filtered_dnt)
    sys_prompt = downstream_prompt_template.format(
        target_lang=target_lang,
        target_lang_lower=target_lang.lower().replace(" ", "_"),
        anchor_glossary=anchor_glossary,
        target_glossary=target_glossary,
        style=style,
        en_text=en_text,
        anchor_text=anchor_text,
        dnt_str=filtered_dnt_str
    )
    prompt = f"{sys_prompt}\n\nTranslate the following English text into {target_lang}:\n<text>\n{en_text}\n</text>"
    raw_translation = generate_with_retry(prompt)
    return validate_translation(str(en_text), raw_translation)

def main():
    input_file = f'{BASE_DIR}/translation_en_es_nl-20260520T063532Z.xlsx'
    output_file = f'{BASE_DIR}/translation_en_de_zh-20260520.xlsx'
    
    print(f"Loading {input_file}...")
    df = pd.read_excel(input_file, header=1)
    df['sv_anchor'] = ""
    df['de'] = ""
    df['zh'] = ""
    
    total_rows = len(df)
    print(f"Total rows: {total_rows}")
    
    # PASS 1: Swedish Anchor (Disambiguation helper)
    print("Pass 1: Translating to Swedish (Anchor)...")
    def process_anchor(idx, row):
        en_text = row['en']
        if is_translatable(en_text):
            sv_text = translate_anchor(en_text)
        else:
            sv_text = en_text if not pd.isna(en_text) else ""
        return idx, sv_text
        
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(process_anchor, idx, row): idx for idx, row in df.iterrows()}
        for future in tqdm(as_completed(futures), total=total_rows, desc="Pass 1 (Swedish Anchor)"):
            idx, sv_text = future.result()
            df.at[idx, 'sv_anchor'] = sv_text
                
    # PASS 2: Downstream (German and Chinese)
    print("Pass 2: Translating to German and Chinese...")
    def process_downstream(idx, row):
        en_text = row['en']
        sv_text = row['sv_anchor']
        if is_translatable(en_text):
            de_text = translate_downstream(en_text, sv_text, "German")
            zh_text = translate_downstream(en_text, sv_text, "Chinese")
        else:
            de_text = en_text if not pd.isna(en_text) else ""
            zh_text = en_text if not pd.isna(en_text) else ""
        return idx, de_text, zh_text

    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(process_downstream, idx, row): idx for idx, row in df.iterrows()}
        for future in tqdm(as_completed(futures), total=total_rows, desc="Pass 2 (German & Chinese)"):
            idx, de_text, zh_text = future.result()
            df.at[idx, 'de'] = de_text
            df.at[idx, 'zh'] = zh_text
                
    # Clean up auxiliary anchor column before saving
    df.drop(columns=['sv_anchor'], inplace=True)
    
    print("Saving to Excel...")
    df.to_excel(output_file, index=False)
    print(f"Done! Saved to {output_file}")

if __name__ == "__main__":
    main()
