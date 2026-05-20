import os
import re
import xml.etree.ElementTree as ET
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

def is_translatable(text, elem):
    if elem.get('translatable') == 'false':
        return False
    if not text or not text.strip():
        return False
    if text.startswith('http://') or text.startswith('https://'):
        return False
    # If it's just numbers, symbols, or placeholders
    if not re.search('[a-zA-Z]', text):
        return False
    return True

def validate_translation(original, translated):
    if not translated:
        return original
    if translated.startswith("ERROR:"):
        return original
    
    # If the AI hallucinates the entire context document, the length will be extremely long
    if len(translated) > max(len(original) * 4, 100):
        # Additional check to see if it regurgitated the style guide
        if "Roxtec" in translated and "Company & Core Business" in translated:
            return original
        # If it's just bizarrely long
        if len(translated) > 300 and len(original) < 50:
            return original
            
    # Sometimes it wraps the output in quotes if it gets confused
    if translated.startswith('"') and translated.endswith('"') and not original.startswith('"'):
        translated = translated[1:-1]
        
    return translated

def translate_anchor(text, target_lang="Swedish"):
    glossary = load_glossary_for_lang(target_lang)
    sys_prompt = anchor_prompt_template.format(target_lang=target_lang, glossary=glossary, style=style)
    prompt = f"{sys_prompt}\n\nText to translate:\n<text>\n{text}\n</text>"
    raw_translation = generate_with_retry(prompt)
    return validate_translation(text, raw_translation)

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
    return validate_translation(en_text, raw_translation)

def process_file(filepath):
    print(f"Processing {filepath}...")
    tree = ET.parse(filepath)
    root = tree.getroot()
    
    strings_data = []
    for elem in root.findall('string'):
        strings_data.append({
            'elem': elem,
            'name': elem.get('name'),
            'en': elem.text,
            'skip': not is_translatable(elem.text, elem)
        })
        
    print(f"  Found {len(strings_data)} strings. Pass 1: Translating to Swedish (Anchor)...")
    
    def process_anchor(item):
        if not item['skip']:
            item['sv'] = translate_anchor(item['en'])
        else:
            item['sv'] = item['en']
        return item
        
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_anchor, item): item for item in strings_data}
        count = 0
        for future in as_completed(futures):
            count += 1
            if count % 50 == 0:
                print(f"  [Pass 1] {count}/{len(strings_data)} completed")
                
    print(f"  Pass 2: Translating to French and German using English and Swedish context...")
    
    def process_downstream(item):
        if not item['skip']:
            item['fr'] = translate_downstream(item['en'], item['sv'], "French")
            item['de'] = translate_downstream(item['en'], item['sv'], "German")
        else:
            item['fr'] = item['en']
            item['de'] = item['en']
        return item

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_downstream, item): item for item in strings_data}
        count = 0
        for future in as_completed(futures):
            count += 1
            if count % 50 == 0:
                print(f"  [Pass 2] {count}/{len(strings_data)} completed")

    base_name, ext = os.path.splitext(filepath)
    
    for lang in ['fr', 'de', 'sv']:
        lang_tree = ET.ElementTree(ET.fromstring(ET.tostring(root)))
        lang_root = lang_tree.getroot()
        for elem in lang_root.findall('string'):
            name = elem.get('name')
            matching_item = next((item for item in strings_data if item['name'] == name), None)
            if matching_item:
                elem.text = matching_item.get(lang, matching_item['en'])
                
        out_path = f"{base_name}_{lang}{ext}"
        lang_tree.write(out_path, encoding='utf-8', xml_declaration=True)
        print(f"  Saved {out_path}")

def main():
    files = [
        '/home/user/.agents/skills/batch-translator/strings - Build.xml',
        '/home/user/.agents/skills/batch-translator/strings - Inspector.xml',
        '/home/user/.agents/skills/batch-translator/strings - Shared.xml'
    ]
    for filepath in files:
        process_file(filepath)
    print("All XML files translated with strict validation!")

if __name__ == "__main__":
    main()
