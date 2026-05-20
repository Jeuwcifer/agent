import pandas as pd
import google.generativeai as genai
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

with open('/home/user/.agents/skills/batch-translator/context/Translationsupport.md', 'r') as f:
    style = f.read()

system_prompt_template = """You are a professional localization expert for Roxtec.
Translate the given text into {target_lang}.
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
    
    for attempt in range(5):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            if '429' in str(e):
                sleep((attempt + 1) * 3) # Backoff
            else:
                return f"ERROR: {str(e)}"
    return "ERROR: Max retries exceeded"

def process_row(index, row_dict):
    en_text = row_dict['en']
    fr_text = translate_text(en_text, "French")
    de_text = translate_text(en_text, "German")
    return index, fr_text, de_text

def main():
    print("Loading Excel...")
    df = pd.read_excel('/home/user/.agents/skills/batch-translator/translation_en_es_nl-20260520T063532Z.xlsx', header=1)
    
    # TEST ONLY: Limit to 5 rows
    df = df.head(5).copy()
    
    df['fr'] = ""
    df['de'] = ""
    
    print(f"Translating {len(df)} rows...")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(process_row, idx, row.to_dict()): idx 
            for idx, row in df.iterrows()
        }
        
        count = 0
        for future in as_completed(futures):
            idx, fr, de = future.result()
            df.at[idx, 'fr'] = fr
            df.at[idx, 'de'] = de
            count += 1
            print(f"Processed {count}/{len(df)}")
                
    print(df[['en', 'fr', 'de']])
    print("Saving to translated_output_test.xlsx...")
    df.to_excel('/home/user/.agents/skills/batch-translator/translated_output_test.xlsx', index=False)
    print("Done!")

if __name__ == "__main__":
    main()
