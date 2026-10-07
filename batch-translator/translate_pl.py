import os
import json
import time
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from tqdm import tqdm
from google import genai
from google.genai import types

BASE_DIR = '/home/user/.agents/skills/batch-translator'
INPUT_FILE = os.path.join(BASE_DIR, 'translation_en_es_nl-20260520T063532Z.xlsx')
OUTPUT_FILE = os.path.join(BASE_DIR, 'translation_pl_output.xlsx')
CHECKPOINT_FILE = os.path.join(BASE_DIR, 'checkpoint_pl.jsonl')

client = genai.Client()

with open(os.path.join(BASE_DIR, 'context/swedish_glossary.json'), 'r', encoding='utf-8') as f:
    sv_glossary = json.load(f)

with open(os.path.join(BASE_DIR, 'context/do_not_translate.json'), 'r', encoding='utf-8') as f:
    dnt_list = json.load(f)

def get_active_dnt(glossary_dict, dnt):
    return [t for t in dnt if not any(re.search(r'\b' + re.escape(t) + r'\b', k, re.IGNORECASE) for k in glossary_dict.keys())]

active_dnt_sv = get_active_dnt(sv_glossary, dnt_list)
active_dnt_target = dnt_list

def should_skip(text):
    if not isinstance(text, str): return True
    text = text.strip()
    if not text: return True
    if re.match(r'^(https?://|ftp://|www\.)', text, re.IGNORECASE): return True
    if 'translatable="false"' in text or "translatable='false'" in text: return True
    if not any(c.isalpha() for c in text): return True
    cleaned = re.sub(r'\{[^}]*\}|<[^>]*>|%[a-zA-Z]', '', text)
    if not any(c.isalpha() for c in cleaned): return True
    return False

def call_gemini(prompt, sys_instr, mime="text/plain"):
    for attempt in range(6):
        try:
            config = types.GenerateContentConfig(system_instruction=sys_instr, temperature=0.0, response_mime_type=mime)
            res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config=config)
            if res.text: return res.text.strip()
            return ""
        except Exception as e:
            if "429" in str(e): time.sleep((2**attempt) + 5)
            elif attempt == 5: return f"ERROR: {e}"
            else: time.sleep(1)
    return "ERROR: Max retries"

def evaluate_translation(source, trans, target_lang, glossary):
    sys_p = f"""Evaluate {target_lang} translation. Check: 1. Glossary. 2. Fluency. 3. Placeholders. 4. DNT terms. Return ONLY valid JSON: {{"passed": true/false, "feedback": "reasoning"}}"""
    prompt = f"<source>\n{source}\n</source>\n<translation>\n{trans}\n</translation>\n<glossary>\n{json.dumps(glossary)}\n</glossary>"
    res = call_gemini(prompt, sys_p, "application/json")
    if res.startswith("ERROR"): return {"passed": True}
    try: return json.loads(res)
    except: return {"passed": True}

def generate_with_critique(en_text, prompt, sys_prompt, lang, glossary):
    trans = call_gemini(prompt, sys_prompt)
    if trans.startswith("ERROR:"): return trans
    eval_res = evaluate_translation(en_text, trans, lang, glossary)
    if not eval_res.get("passed", True):
        critique = f"{prompt}\n\n<critique>\nPrevious translation: {trans}\nFailed: {eval_res.get('feedback')}\nReturn corrected translation ONLY.\n</critique>"
        trans_new = call_gemini(critique, sys_prompt)
        if not trans_new.startswith("ERROR:"): return trans_new
    return trans

def process_row(idx, row):
    en_text = row['en']
    if should_skip(en_text): return idx, en_text, en_text

    sys_sv = f"Translate English to Swedish. Preserve placeholders. Return ONLY translation.\n<glossary>{json.dumps(sv_glossary)}</glossary>\n<dnt>{json.dumps(active_dnt_sv)}</dnt>"
    sv_trans = generate_with_critique(en_text, en_text, sys_sv, "Swedish", sv_glossary)
    if sv_trans.startswith("ERROR:"): sv_trans = en_text

    sys_pl = f"Translate English to Polish. Use Swedish anchor for context. Preserve placeholders. Return ONLY translation.\n<anchor_glossary>{json.dumps(sv_glossary)}</anchor_glossary>\n<dnt>{json.dumps(active_dnt_target)}</dnt>"
    p_pl = f"<source>{en_text}</source>\n<anchor_swedish>{sv_trans}</anchor_swedish>"
    pl_trans = generate_with_critique(en_text, p_pl, sys_pl, "Polish", {})
    if pl_trans.startswith("ERROR:"): pl_trans = en_text

    return idx, sv_trans, pl_trans

def main():
    df = pd.read_excel(INPUT_FILE, header=1)
    df['sv'], df['pl'] = "", ""
    
    chkpt = {}
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            for line in f:
                d = json.loads(line)
                chkpt[int(d['idx'])] = (d['sv'], d['pl'])
    
    for idx, (sv, pl) in chkpt.items():
        if idx in df.index:
            df.at[idx, 'sv'], df.at[idx, 'pl'] = sv, pl

    pending = [(idx, row.to_dict()) for idx, row in df.iterrows() if idx not in chkpt]
    limit = int(os.environ.get('LIMIT_TEST', 0))
    if limit > 0: pending = pending[:limit]
    
    if pending:
        with ThreadPoolExecutor(max_workers=15) as exe:
            futs = {exe.submit(process_row, i, r): i for i, r in pending}
            with open(CHECKPOINT_FILE, 'a') as cf:
                for f in tqdm(as_completed(futs), total=len(futs), desc="Translating PL"):
                    idx, sv, pl = f.result()
                    df.at[idx, 'sv'], df.at[idx, 'pl'] = sv, pl
                    cf.write(json.dumps({'idx': idx, 'sv': sv, 'pl': pl}) + '\n')
                    cf.flush()

    cols = ['ID', 'Comment', 'Master', 'en', 'es', 'nl', 'sv', 'pl']
    df[cols].to_excel(OUTPUT_FILE, index=False)

if __name__ == '__main__':
    main()