import os
import re
import json
import pandas as pd
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep
from tqdm import tqdm

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
model = genai.GenerativeModel('gemini-2.5-flash')

# Load Context
with open('/home/user/.agents/skills/batch-translator/context/Translationsupport.md', 'r') as f:
    style = f.read()
with open('/home/user/.agents/skills/batch-translator/context/do_not_translate.json', 'r') as f:
    dnt_list = json.load(f)
dnt_str = ", ".join(dnt_list)

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

GLOSSARY_DIR = '/home/user/.agents/skills/batch-translator/context'

def load_glossary_for_lang(lang_name):
    lang_mapping = {
        'swedish': 'swedish_glossary.json',
        'sv': 'swedish_glossary.json',
        'french': 'french_glossary.json',
        'fr': 'french_glossary.json',
        'polish': 'polish_glossary.json',
        'pl': 'polish_glossary.json'
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
            pass
    return ""

def get_filtered_dnt_list(target_lang):
    filtered_dnt = list(dnt_list)
    lang_mapping = {
        'swedish': 'swedish_glossary.json',
        'sv': 'swedish_glossary.json',
        'french': 'french_glossary.json',
        'fr': 'french_glossary.json',
        'polish': 'polish_glossary.json',
        'pl': 'polish_glossary.json'
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
    if 'translatable="false"' in text or "translatable='false'" in text:
        return False
    # skip if no letters
    cleaned = re.sub(r'\{[^}]*\}|<[^>]*>|%[a-zA-Z]', '', text)
    if not any(c.isalpha() for c in cleaned):
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
    output_file = '/home/user/.agents/skills/batch-translator/translation_en_es_nl_sv_pl.xlsx'
    chkpt_file = '/home/user/.agents/skills/batch-translator/checkpoint_new_pl.jsonl'
    
    print(f"Loading {input_file}...")
    df = pd.read_excel(input_file, header=1)
    
    if 'sv' not in df.columns:
        df['sv'] = ""
    if 'pl' not in df.columns:
        df['pl'] = ""
        
    chkpt = {}
    if os.path.exists(chkpt_file):
        with open(chkpt_file, 'r') as f:
            for line in f:
                d = json.loads(line)
                chkpt[int(d['idx'])] = (d['sv'], d['pl'])
    
    for idx, (sv, pl) in chkpt.items():
        if idx in df.index:
            df.at[idx, 'sv'], df.at[idx, 'pl'] = sv, pl

    total_rows = len(df)
    pending = [(idx, row.to_dict()) for idx, row in df.iterrows() if idx not in chkpt]
    print(f"Total rows: {total_rows}, Pending: {len(pending)}")
    
    def process_row(idx, row):
        en_text = row['en']
        if not is_translatable(en_text):
            return idx, en_text if not pd.isna(en_text) else "", en_text if not pd.isna(en_text) else ""
            
        sv_text = translate_anchor(en_text)
        pl_text = translate_downstream(en_text, sv_text, "Polish")
        return idx, sv_text, pl_text

    if pending:
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(process_row, idx, row): idx for idx, row in pending}
            with open(chkpt_file, 'a') as cf:
                for future in tqdm(as_completed(futures), total=len(futures), desc="Translating to Polish"):
                    idx, sv_text, pl_text = future.result()
                    df.at[idx, 'sv'] = sv_text
                    df.at[idx, 'pl'] = pl_text
                    cf.write(json.dumps({'idx': idx, 'sv': sv_text, 'pl': pl_text}) + '\n')
                    cf.flush()
                
    print("Saving to Excel...")
    df.to_excel(output_file, index=False)
    print(f"Done! Saved to {output_file}")

if __name__ == "__main__":
    main()
