import pandas as pd
import google.generativeai as genai
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

with open('/home/user/.agents/skills/batch-translator/context/Translationsupport.md', 'r') as f:
    style = f.read()

system_prompt_template = """You are a professional localization expert for Roxtec.
Translate the given text into {target_lang}.
Preserve any placeholders like {{0}}, {{1}}, %s, HTML tags, or formatting.

Reference contexts for terminology and style constraints:
<glossary>
{glossary}
</glossary>

<style_guide>
{style}
</style_guide>

Return strictly the translated text, nothing else. No markdown wrappers or explanations.
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

def translate_text(text, target_lang):
    if pd.isna(text) or not str(text).strip():
        return text
        
    glossary = load_glossary_for_lang(target_lang)
    sys_prompt = system_prompt_template.format(target_lang=target_lang, glossary=glossary, style=style)
    prompt = f"{sys_prompt}\n\nText to translate:\n{text}"
    
    for attempt in range(8):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            err_msg = str(e)
            if '429' in err_msg or 'Quota' in err_msg or 'exhausted' in err_msg.lower():
                sleep((attempt + 1) * 5) # Exponential-ish backoff
            else:
                sleep(2) # minor wait for other errors
    return "ERROR: Max retries exceeded"

def process_row(index, row_dict):
    en_text = row_dict['en']
    sv_text = translate_text(en_text, "Swedish")
    return index, sv_text

def main():
    input_path = '/home/user/.agents/skills/batch-translator/translation_fr_de_completed.xlsx'
    output_path = '/home/user/.agents/skills/batch-translator/translation_fr_de_sv_completed.xlsx'
    
    print(f"Loading Excel from {input_path}...")
    df = pd.read_excel(input_path)
    
    df['sv'] = ""
    
    total_rows = len(df)
    print(f"Translating {total_rows} rows to Swedish...")
    
    # Parallel processing
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(process_row, idx, row.to_dict()): idx 
            for idx, row in df.iterrows()
        }
        
        count = 0
        for future in as_completed(futures):
            idx, sv = future.result()
            df.at[idx, 'sv'] = sv
            count += 1
            if count % 100 == 0 or count == total_rows:
                print(f"Processed {count}/{total_rows}")
                
    print("Formatting output...")
    df.to_excel(output_path, index=False)
    print(f"Saved completed translations to {output_path}")

if __name__ == "__main__":
    main()
