import os
import re
import json
import pandas as pd
import numpy as np
from google import genai
from google.genai import types
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep
from tqdm import tqdm

# Initialize GenAI client
client = genai.Client()

GLOSSARY_DIR = '/home/user/.agents/skills/batch-translator/context'
STYLE_PATH = os.path.join(GLOSSARY_DIR, 'Translationsupport.md')
DNT_PATH = os.path.join(GLOSSARY_DIR, 'do_not_translate.json')

# Load style guide and DNT list
with open(STYLE_PATH, 'r') as f:
    style_guide = f.read()

with open(DNT_PATH, 'r') as f:
    raw_dnt_list = json.load(f)

# System prompt templates
pass1_system_prompt_template = """You are a professional localization expert for Roxtec, a Swedish global company providing sealing solutions for cable and pipe penetrations.
Translate the given English text into Swedish.
Preserve any placeholders like {{0}}, {{1}}, %s, or HTML tags exactly.

CRITICAL INSTRUCTIONS:
1. If a term is defined in the Swedish glossary below, it MUST be translated according to the glossary. This has the absolute highest priority.
2. If a term is in the "Do Not Translate" list below, and is NOT overridden by the Swedish glossary, it MUST NOT be translated and must remain exactly as it appears:
{dnt_str}

<swedish_glossary>
{swedish_glossary}
</swedish_glossary>

<style_guide>
{style}
</style_guide>

Return strictly the translated Swedish text, nothing else. No markdown wrappers, no explanations, no quotes unless present in the original. Do not comment on the translation.
"""

pass2_system_prompt_template = """You are a professional localization expert for Roxtec.
Translate the given English text into {target_lang}.
Preserve any placeholders like {{0}}, {{1}}, %s, or HTML tags exactly.

CRITICAL INSTRUCTIONS:
1. If a term is defined in the target glossary (<target_glossary_{target_lang_lower}>), it MUST be translated according to that glossary. This has the absolute highest priority.
2. If a term is in the "Do Not Translate" list below, and is NOT overridden by the target glossary, it MUST NOT be translated and must remain exactly as it appears:
{dnt_str}

Reference contexts for terminology and style constraints:

<anchor_glossary_swedish>
Use this primary Swedish glossary to disambiguate English terms (since Swedish is the core domain language of Roxtec):
{anchor_glossary}
</anchor_glossary_swedish>

{target_glossary_xml}

<style_guide>
{style}
</style_guide>

To help with precise translation and disambiguation, you will be provided with both the English source and its Swedish anchor translation in XML tags. Use the Swedish anchor translation and the Swedish glossary to resolve any ambiguity in the English terms.

Return strictly the translated {target_lang} text, nothing else. No markdown wrappers, no explanations, no quotes unless present in the original. Do not comment on the translation.
"""

def load_glossary_for_lang(lang_name):
    lang_mapping = {
        'swedish': 'swedish_glossary.json',
        'sv': 'swedish_glossary.json',
        'french': 'french_glossary.json',
        'fr': 'french_glossary.json',
        'danish': 'danish_glossary.json',
        'da': 'danish_glossary.json'
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
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load glossary file {filepath}: {e}")
    return {}

def get_filtered_dnt_list(target_lang, glossary_dict, dnt_list):
    if not glossary_dict:
        return list(dnt_list)
    
    filtered_dnt = []
    glossary_keys_lower = [str(k).lower().strip() for k in glossary_dict.keys()]
    
    for term in dnt_list:
        term_lower = str(term).lower().strip()
        conflict = False
        for gk in glossary_keys_lower:
            if term_lower in gk or gk in term_lower:
                conflict = True
                break
        if not conflict:
            filtered_dnt.append(term)
            
    return filtered_dnt

def is_translatable(text):
    if pd.isna(text):
        return False
    text_str = str(text).strip()
    if not text_str:
        return False
    if text_str.startswith('http://') or text_str.startswith('https://'):
        return False
    if 'translatable="false"' in text_str or 'translatable=\'false\'' in text_str:
        return False
        
    cleaned = text_str
    cleaned = re.sub(r'\{\d+\}', '', cleaned)
    cleaned = re.sub(r'%\d+\$[s|d|f]', '', cleaned)
    cleaned = re.sub(r'%[s|d|f]', '', cleaned)
    
    if not re.search('[a-zA-Z]', cleaned):
        return False
    return True

def validate_translation(original, translated):
    if not translated or str(translated).startswith("ERROR:"):
        return original
        
    original_str = str(original).strip()
    translated_str = str(translated).strip()
    
    # Check if translation is abnormally long or contains system-prompt instructions/style guide text
    original_len = len(original_str)
    translated_len = len(translated_str)
    
    hallucination_indicators = [
        "Roxtec Software Suite", "Digital Chain", "Roxtec Transit Designer", 
        "Roxtec Transit Build", "Roxtec Transit Operate", "You are a professional localization expert", 
        "Translate the given text", "Do Not Translate"
    ]
    contains_style_words = any(indicator.lower() in translated_str.lower() for indicator in hallucination_indicators)
    
    if contains_style_words:
        return original_str
        
    if original_len > 0 and translated_len > max(original_len * 4, 100):
        return original_str
        
    # Strip unnecessary surrounding quotes if they weren't in the original text
    if translated_str.startswith('"') and translated_str.endswith('"') and not original_str.startswith('"'):
        translated_str = translated_str[1:-1].strip()
    elif translated_str.startswith("'") and translated_str.endswith("'") and not original_str.startswith("'"):
        translated_str = translated_str[1:-1].strip()
        
    return translated_str

def generate_with_retry(system_instruction, contents):
    for attempt in range(8):
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0
            )
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=contents,
                config=config
            )
            return response.text.strip()
        except Exception as e:
            err_msg = str(e)
            if '429' in err_msg or 'Quota' in err_msg or 'exhausted' in err_msg.lower():
                sleep((attempt + 1) * 3)
            else:
                sleep(1.5)
    return "ERROR: Max retries exceeded"

def main():
    input_file = '/home/user/.agents/skills/batch-translator/translation_en_es_nl-20260520T063532Z.xlsx'
    output_file = '/home/user/.agents/skills/batch-translator/translation_en_es_nl_fr_da.xlsx'
    
    print(f"Loading input file: {input_file}...")
    df = pd.read_excel(input_file, header=1)
    
    # Step 1: Identify all unique English strings that require translation
    all_en_values = df['en'].tolist()
    unique_translatable_en = sorted(list({str(val).strip() for val in all_en_values if is_translatable(val)}))
    
    print(f"Total rows in sheet: {len(df)}")
    print(f"Total unique translatable English strings: {len(unique_translatable_en)}")
    
    # Prepare glossaries
    swedish_glossary = load_glossary_for_lang("Swedish")
    french_glossary = load_glossary_for_lang("French")
    
    # Filter DNT list per language to prevent conflict with glossary
    dnt_sv = get_filtered_dnt_list("Swedish", swedish_glossary, raw_dnt_list)
    dnt_fr = get_filtered_dnt_list("French", french_glossary, raw_dnt_list)
    dnt_da = get_filtered_dnt_list("Danish", {}, raw_dnt_list) # Danish has no glossary, so full DNT list applies
    
    dnt_sv_str = ", ".join(dnt_sv)
    dnt_fr_str = ", ".join(dnt_fr)
    dnt_da_str = ", ".join(dnt_da)
    
    # Format glossaries for prompt injection
    swedish_glossary_json = json.dumps(swedish_glossary, indent=2, ensure_ascii=False)
    french_glossary_json = json.dumps(french_glossary, indent=2, ensure_ascii=False)
    
    # Target glossary XMLs
    french_glossary_xml = f"""<target_glossary_french>
{french_glossary_json}
</target_glossary_french>"""
    danish_glossary_xml = "" # Danish has no glossary
    
    # Mappings from English -> Target Translation
    en_to_sv_mapping = {}
    en_to_fr_mapping = {}
    en_to_da_mapping = {}
    
    # PASS 1: Translate to Swedish (Anchor)
    print("\n--- PASS 1: Translating unique strings to Swedish (Anchor) ---")
    
    # Construct Swedish instruction
    sv_system_instruction = pass1_system_prompt_template.format(
        dnt_str=dnt_sv_str,
        swedish_glossary=swedish_glossary_json,
        style=style_guide
    )
    
    def process_sv_translation(en_text):
        user_content = f"<text>\n{en_text}\n</text>"
        raw_res = generate_with_retry(sv_system_instruction, user_content)
        validated_res = validate_translation(en_text, raw_res)
        return en_text, validated_res
        
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(process_sv_translation, text): text for text in unique_translatable_en}
        for future in tqdm(as_completed(futures), total=len(unique_translatable_en), desc="Translating (English -> Swedish)"):
            en_text, sv_text = future.result()
            en_to_sv_mapping[en_text] = sv_text
            
    # PASS 2: Translate to French and Danish (Downstream)
    print("\n--- PASS 2: Translating unique strings to French and Danish (using Swedish Anchor) ---")
    
    # Construct downstream instructions
    fr_system_instruction = pass2_system_prompt_template.format(
        target_lang="French",
        target_lang_lower="french",
        dnt_str=dnt_fr_str,
        anchor_glossary=swedish_glossary_json,
        target_glossary_xml=french_glossary_xml,
        style=style_guide
    )
    
    da_system_instruction = pass2_system_prompt_template.format(
        target_lang="Danish",
        target_lang_lower="danish",
        dnt_str=dnt_da_str,
        anchor_glossary=swedish_glossary_json,
        target_glossary_xml=danish_glossary_xml,
        style=style_guide
    )
    
    def process_fr_translation(en_text, sv_text):
        user_content = f"""<english_source>
{en_text}
</english_source>
<swedish_anchor>
{sv_text}
</swedish_anchor>"""
        raw_res = generate_with_retry(fr_system_instruction, user_content)
        validated_res = validate_translation(en_text, raw_res)
        return en_text, validated_res
        
    def process_da_translation(en_text, sv_text):
        user_content = f"""<english_source>
{en_text}
</english_source>
<swedish_anchor>
{sv_text}
</swedish_anchor>"""
        raw_res = generate_with_retry(da_system_instruction, user_content)
        validated_res = validate_translation(en_text, raw_res)
        return en_text, validated_res
        
    # Translate to French
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {
            executor.submit(process_fr_translation, text, en_to_sv_mapping[text]): text 
            for text in unique_translatable_en
        }
        for future in tqdm(as_completed(futures), total=len(unique_translatable_en), desc="Translating (English -> French)"):
            en_text, fr_text = future.result()
            en_to_fr_mapping[en_text] = fr_text
            
    # Translate to Danish
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {
            executor.submit(process_da_translation, text, en_to_sv_mapping[text]): text 
            for text in unique_translatable_en
        }
        for future in tqdm(as_completed(futures), total=len(unique_translatable_en), desc="Translating (English -> Danish)"):
            en_text, da_text = future.result()
            en_to_da_mapping[en_text] = da_text
            
    # Now, map all translations back to the DataFrame
    print("\nMapping translations back to spreadsheet...")
    
    fr_column_values = []
    da_column_values = []
    
    for val in all_en_values:
        if pd.isna(val):
            fr_column_values.append(np.nan)
            da_column_values.append(np.nan)
        else:
            val_str = str(val).strip()
            if is_translatable(val_str):
                fr_column_values.append(en_to_fr_mapping.get(val_str, val_str))
                da_column_values.append(en_to_da_mapping.get(val_str, val_str))
            else:
                # If non-translatable, write original value
                fr_column_values.append(val)
                da_column_values.append(val)
                
    df['fr'] = fr_column_values
    df['da'] = da_column_values
    
    # Save with identical structure: empty first row, headers on row 1, followed by rows of data.
    headers = ['ID', 'Comment', 'Master', 'en', 'es', 'nl', 'fr', 'da']
    output_rows = []
    # Row 0 is empty
    output_rows.append([np.nan] * len(headers))
    # Row 1 is headers
    output_rows.append(headers)
    # The rest is dataframe data
    for idx, row in df.iterrows():
        output_rows.append([
            row['ID'],
            row['Comment'],
            row['Master'],
            row['en'],
            row['es'],
            row['nl'],
            row['fr'],
            row['da']
        ])
        
    df_final = pd.DataFrame(output_rows)
    df_final.to_excel(output_file, index=False, header=False)
    
    print(f"\nSuccessfully finished translation!")
    print(f"Results saved to: {output_file}")
    
    # Let's print a small sample of the results
    print("\nSample translations (first 3 translatable rows):")
    sample_count = 0
    for idx, row in df.iterrows():
        en = row['en']
        if is_translatable(en):
            print(f"\nID: {row['ID']}")
            print(f"EN: {en}")
            print(f"FR: {row['fr']}")
            print(f"DA: {row['da']}")
            sample_count += 1
            if sample_count >= 3:
                break

if __name__ == "__main__":
    main()
