import os
import re
import pandas as pd
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# Load Context
with open('/home/user/.agents/skills/batch-translator/context/Translationsupport.md', 'r') as f:
    style = f.read()

anchor_prompt_template = """You are a professional localization expert for Roxtec.
Translate the given text from English into {target_lang}.
Preserve any placeholders like {{0}}, {{1}}, %s, or HTML tags.

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

GLOSSARY_DIR = '/home/user/.agents/skills/batch-translator/context'

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

def generate_with_retry(prompt):
    for attempt in range(8):
        try:
            response = model.generate_content(prompt)
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
        if "Roxtec" in translated and "Company & Core Business" in translated:
            return original
        if len(translated) > 300 and original_len < 50:
            return original
            
    if translated.startswith('"') and translated.endswith('"') and not str(original).startswith('"'):
        translated = translated[1:-1]
        
    return translated

def translate_anchor(text, target_lang="Swedish"):
    glossary = load_glossary_for_lang(target_lang)
    sys_prompt = anchor_prompt_template.format(target_lang=target_lang, glossary=glossary, style=style)
    prompt = f"{sys_prompt}\n\nText to translate:\n<text>\n{text}\n</text>"
    raw_translation = generate_with_retry(prompt)
    return validate_translation(str(text), raw_translation)

def translate_downstream(en_text, anchor_text, target_lang, anchor_lang="Swedish"):
    anchor_glossary = load_glossary_for_lang(anchor_lang)
    target_glossary = load_glossary_for_lang(target_lang)
    sys_prompt = downstream_prompt_template.format(
        target_lang=target_lang,
        target_lang_lower=target_lang.lower().replace(" ", "_"),
        anchor_glossary=anchor_glossary,
        target_glossary=target_glossary,
        style=style,
        anchor_lang=anchor_lang,
        en_text=en_text,
        anchor_text=anchor_text
    )
    prompt = f"{sys_prompt}\n\nTranslate the following English text into {target_lang}:\n<text>\n{en_text}\n</text>"
    raw_translation = generate_with_retry(prompt)
    return validate_translation(str(en_text), raw_translation)

def main():
    input_file = '/home/user/.agents/skills/batch-translator/translation_en_es_nl-20260520T063532Z.xlsx'
    output_file = '/home/user/.agents/skills/batch-translator/translation_en_es_nl_sv_zh_no-20260520.xlsx'
    
    print(f"Loading {input_file}...")
    df_raw = pd.read_excel(input_file, header=None)
    headers = df_raw.iloc[0].tolist()
    
    df = pd.read_excel(input_file, header=1)
    df['sv'] = ""
    df['zh'] = ""
    df['no'] = ""
    
    total_rows = len(df)
    print(f"Total translatable rows: {total_rows}")
    
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
        count = 0
        for future in as_completed(futures):
            idx, sv_text = future.result()
            df.at[idx, 'sv'] = sv_text
            count += 1
            if count % 100 == 0:
                print(f"  [Pass 1] {count}/{total_rows}")
                
    # PASS 2: Downstream Languages
    print("Pass 2: Translating to Chinese (Simplified) and Norwegian...")
    def process_downstream(idx, row):
        en_text = row['en']
        sv_text = row['sv']
        if is_translatable(en_text):
            zh_text = translate_downstream(en_text, sv_text, "Chinese (Simplified)")
            no_text = translate_downstream(en_text, sv_text, "Norwegian")
        else:
            zh_text = en_text if not pd.isna(en_text) else ""
            no_text = en_text if not pd.isna(en_text) else ""
        return idx, zh_text, no_text

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_downstream, idx, row): idx for idx, row in df.iterrows()}
        count = 0
        for future in as_completed(futures):
            idx, zh_text, no_text = future.result()
            df.at[idx, 'zh'] = zh_text
            df.at[idx, 'no'] = no_text
            count += 1
            if count % 100 == 0:
                print(f"  [Pass 2] {count}/{total_rows}")
                
    print("Saving to Excel...")
    df.to_excel(output_file, index=False)
    print(f"Done! Saved to {output_file}")

if __name__ == "__main__":
    main()
