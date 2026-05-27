import os
import re
import json
import pandas as pd
from google import genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep
from tqdm import tqdm

client = genai.Client()

# Load Context files from the skill's context directory
CONTEXT_DIR = '/home/user/.agents/skills/batch-translator/context'
with open(os.path.join(CONTEXT_DIR, 'Translationsupport.md'), 'r') as f:
    style = f.read()
with open(os.path.join(CONTEXT_DIR, 'do_not_translate.json'), 'r') as f:
    dnt_list = json.load(f)

anchor_prompt_template = """You are a professional localization expert for Roxtec.
Translate the given text from English into {target_lang}.
Preserve any placeholders like {{0}}, {{1}}, %s, or HTML tags.

CRITICAL INSTRUCTION:
1. If a term is defined in the target language glossary (e.g., <glossary>), it MUST be translated according to the glossary. This has the absolute highest priority.
2. If a term is in the list below, and is NOT overridden by the glossary, it MUST NOT be translated and must remain exactly as it appears:
{dnt_str}

Reference contexts for terminology and style constraints:
<glossary>
{glossary}
</glossary>
<style_guide>
{style}
</style_guide>

Return strictly the translated text, nothing else. No markdown wrappers or explanations.
"""

downstream_prompt_template = """You are a professional localization expert for Roxtec.
Translate the given text into {target_lang}.
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

To help with disambiguation, here is the English source and its {anchor_lang} translation:
English: {en_text}
{anchor_lang}: {anchor_text}

Return strictly the {target_lang} translated text for the English source. Do not return any explanations, markdown, or the style guide.
"""

def load_glossary_for_lang(lang_name):
    lang_mapping = {
        'swedish': 'swedish_glossary.json',
        'sv': 'swedish_glossary.json',
        'french': 'french_glossary.json',
        'fr': 'french_glossary.json'
    }
    key = str(lang_name).lower().strip()
    filename = lang_mapping.get(key)
    if not filename:
        possible_filename = f"{key}_glossary.json"
        if os.path.exists(os.path.join(CONTEXT_DIR, possible_filename)):
            filename = possible_filename
            
    if filename:
        filepath = os.path.join(CONTEXT_DIR, filename)
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
        'french': 'french_glossary.json',
        'fr': 'french_glossary.json'
    }
    key = str(target_lang).lower().strip()
    filename = lang_mapping.get(key)
    if not filename:
        possible_filename = f"{key}_glossary.json"
        if os.path.exists(os.path.join(CONTEXT_DIR, possible_filename)):
            filename = possible_filename
            
    if filename:
        filepath = os.path.join(CONTEXT_DIR, filename)
        try:
            with open(filepath, 'r') as f:
                glossary_dict = json.load(f)
                glossary_keys = {str(k).lower().strip() for k in glossary_dict.keys()}
                # Filter out terms where the term itself or its singular form conflicts with the glossary
                filtered_dnt = [
                    term for term in filtered_dnt 
                    if term.lower().strip() not in glossary_keys and term.lower().strip().rstrip('s') not in glossary_keys
                ]
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
    # Strict post-processing validation of hallucination or style guide leaking
    if len(translated) > max(original_len * 4, 100):
        if "Roxtec" in translated and "Company & Core Business" in translated:
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

def translate_downstream(en_text, anchor_text, target_lang, anchor_lang="Swedish"):
    anchor_glossary = load_glossary_for_lang(anchor_lang)
    target_glossary = load_glossary_for_lang(target_lang)
    filtered_dnt = get_filtered_dnt_list(target_lang)
    filtered_dnt_str = ", ".join(filtered_dnt)
    sys_prompt = downstream_prompt_template.format(
        target_lang=target_lang,
        target_lang_lower=target_lang.lower().replace(" ", "_"),
        anchor_glossary=anchor_glossary,
        target_glossary=target_glossary,
        style=style,
        anchor_lang=anchor_lang,
        en_text=en_text,
        anchor_text=anchor_text,
        dnt_str=filtered_dnt_str
    )
    prompt = f"{sys_prompt}\n\nTranslate the following English text into {target_lang}:\n<text>\n{en_text}\n</text>"
    raw_translation = generate_with_retry(prompt)
    return validate_translation(str(en_text), raw_translation)

def main():
    input_file = '/home/user/.agents/skills/batch-translator/translation_en_es_nl-20260520T063532Z.xlsx'
    output_file = '/home/user/.agents/skills/batch-translator/translation_en_es_nl_fr_de.xlsx'
    
    print(f"Loading {input_file}...")
    # Load with header=1 to get the dataframe we want to process
    df = pd.read_excel(input_file, header=1)
    df['sv'] = ""
    df['fr'] = ""
    df['de'] = ""
    
    total_rows = len(df)
    print(f"Total rows to process: {total_rows}")
    
    # PASS 1: Swedish Anchor
    print("Pass 1: Translating to Swedish (Anchor)...")
    def process_anchor(idx, row):
        en_text = row['en']
        if is_translatable(en_text):
            sv_text = translate_anchor(en_text)
        else:
            sv_text = en_text if not pd.isna(en_text) else ""
        return idx, sv_text
        
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_anchor, idx, row): idx for idx, row in df.iterrows()}
        for future in tqdm(as_completed(futures), total=total_rows, desc="Pass 1 (Swedish Anchor)"):
            idx, sv_text = future.result()
            df.at[idx, 'sv'] = sv_text
                
    # PASS 2: Downstream Languages (French and German)
    print("Pass 2: Translating to French and German...")
    def process_downstream(idx, row):
        en_text = row['en']
        sv_text = row['sv']
        if is_translatable(en_text):
            fr_text = translate_downstream(en_text, sv_text, "French")
            de_text = translate_downstream(en_text, sv_text, "German")
        else:
            fr_text = en_text if not pd.isna(en_text) else ""
            de_text = en_text if not pd.isna(en_text) else ""
        return idx, fr_text, de_text

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_downstream, idx, row): idx for idx, row in df.iterrows()}
        for future in tqdm(as_completed(futures), total=total_rows, desc="Pass 2 (French & German)"):
            idx, fr_text, de_text = future.result()
            df.at[idx, 'fr'] = fr_text
            df.at[idx, 'de'] = de_text
                
    print("Reconstructing final sheet with empty row 0 and headers on row 1...")
    # Construct rows list
    output_rows = []
    
    # Row 0: Empty/NaN row (9 columns matching new width)
    output_rows.append([None] * 9)
    
    # Row 1: Headers
    output_rows.append(['ID', 'Comment', 'Master', 'en', 'es', 'nl', 'sv', 'fr', 'de'])
    
    # Rest of the rows: actual translated data
    for _, row in df.iterrows():
        output_rows.append([
            row['ID'],
            row['Comment'],
            row['Master'],
            row['en'],
            row['es'],
            row['nl'],
            row['sv'],
            row['fr'],
            row['de']
        ])
        
    final_df = pd.DataFrame(output_rows)
    print(f"Saving completed translation to {output_file}...")
    final_df.to_excel(output_file, index=False, header=False)
    print("Successfully saved and completed!")

if __name__ == "__main__":
    main()
