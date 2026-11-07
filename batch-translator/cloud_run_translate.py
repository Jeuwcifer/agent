import os
import sys
import re
import json
import time
import random
import tempfile
import pandas as pd
from google import genai
from google.genai import types
from google.cloud import storage
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GLOSSARY_DIR = os.path.join(BASE_DIR, "context")

LANG_FILES = {
    "swedish": "swedish_glossary.json",
    "sv": "swedish_glossary.json",
    "french": "french_glossary.json",
    "fr": "french_glossary.json",
    "spanish": "spanish_glossary.json",
    "es": "spanish_glossary.json",
    "dutch": "dutch_glossary.json",
    "nl": "dutch_glossary.json",
    "german": "german_glossary.json",
    "de": "german_glossary.json",
}

LANG_NAMES = {
    "sv": "Swedish",
    "es": "Spanish",
    "nl": "Dutch",
    "fr": "French",
    "de": "German",
    "pl": "Polish",
    "zh": "Chinese (Simplified)",
    "no": "Norwegian",
}


def load_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Failed to load {filepath}: {e}", file=sys.stderr)
        return ""


def load_json(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load {filepath}: {e}", file=sys.stderr)
        return []


def load_glossary_for_lang(lang_code):
    key = str(lang_code).lower().strip()
    filename = LANG_FILES.get(key, f"{key}_glossary.json")
    filepath = os.path.join(GLOSSARY_DIR, filename)
    if os.path.exists(filepath):
        data = load_json(filepath)
        return data if isinstance(data, dict) else {}
    return {}


def get_active_dnt(glossary_dict, dnt_list):
    glossary_keys = {str(k).lower().strip() for k in glossary_dict.keys()}
    return [t for t in dnt_list if str(t).lower().strip() not in glossary_keys]


def is_translatable(text):
    if text is None or pd.isna(text):
        return False
    text_str = str(text).strip()
    if not text_str:
        return False
    if re.match(r"^(https?://|ftp://|www\.)", text_str, re.IGNORECASE):
        return False
    if 'translatable="false"' in text_str or "translatable='false'" in text_str:
        return False
    if not any(c.isalpha() for c in text_str):
        return False
    cleaned = re.sub(r"\{[^}]*\}|%\d*\$?[a-zA-Z]|<[^>]*>", "", text_str)
    return any(c.isalpha() for c in cleaned)


def validate_translation(original, translated):
    if not translated or translated.startswith("ERROR:"):
        return original
    orig_str = str(original).strip()
    trans_str = str(translated).strip()

    if (trans_str.startswith('"') and trans_str.endswith('"')) or (
        trans_str.startswith("'") and trans_str.endswith("'")
    ):
        if not (
            (orig_str.startswith('"') and orig_str.endswith('"'))
            or (orig_str.startswith("'") and orig_str.endswith("'"))
        ):
            trans_str = trans_str[1:-1].strip()

    if len(orig_str) > 10 and len(trans_str) >= 4 * len(orig_str):
        return original

    hallucination_indicators = [
        "style_guide",
        "style guide",
        "glossary",
        "do_not_translate",
        "translation:",
        "here is",
        "sure, here",
        "Company & Core Business",
        "Digital Ecosystem",
    ]
    for ind in hallucination_indicators:
        if ind.lower() in trans_str.lower() and ind.lower() not in orig_str.lower():
            return original

    return trans_str


def call_gemini(client, prompt, system_instruction, model_name, max_attempts=6):
    for attempt in range(max_attempts):
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0,
            )
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            return response.text.strip() if response.text else ""
        except Exception as e:
            err_str = str(e)
            print(f"Gemini error (attempt {attempt + 1}): {err_str}", file=sys.stderr)
            if "400" in err_str or "INVALID_ARGUMENT" in err_str:
                return f"ERROR: {err_str}"
            if attempt == max_attempts - 1:
                return f"ERROR: {err_str}"
            sleep_time = (2**attempt) * 1.5 + random.uniform(0.5, 1.5)
            if "429" in err_str or "quota" in err_str.lower():
                sleep_time += 5
            time.sleep(sleep_time)
    return "ERROR: Max retries exceeded"


def build_anchor_prompt(style_guide, sv_glossary, sv_dnt):
    return f"""You are a professional localization expert for Roxtec.
Translate the given text in <source_english_text> from English into Swedish (Svenska) as the primary domain reference.

Follow these strict guidelines:
1. Preserve all placeholders like {{0}}, {{1}}, %s, %d, and HTML/XML tags or math symbols (<, >) exactly.
2. Glossary has highest priority: If a term is in <glossary>, translate it according to that glossary.
3. Terms in <do_not_translate> must remain exactly as in source text unless overridden by the glossary.
4. Use <developer_comment> only for disambiguation; NEVER translate or output it.
5. Return ONLY the translated Swedish text.

<style_guide>
{style_guide}
</style_guide>

<glossary>
{json.dumps(sv_glossary, ensure_ascii=False, indent=2)}
</glossary>

<do_not_translate>
{json.dumps(sv_dnt, ensure_ascii=False, indent=2)}
</do_not_translate>"""


def build_target_prompt(lang_code, style_guide, sv_glossary, target_glossary, target_dnt):
    lang_name = LANG_NAMES.get(lang_code, lang_code)
    tag_lang = re.sub(r"[^a-z0-9_]", "_", lang_name.lower())
    return f"""You are a professional localization expert for Roxtec.
Translate the given English text in <source_english_text> into {lang_name}.

Follow these strict guidelines:
1. Preserve all placeholders like {{0}}, {{1}}, %s, %d, and HTML/XML tags or math symbols (<, >) exactly.
2. Glossary priority: If a term is in <target_glossary_{tag_lang}>, you MUST use that translation.
3. Terms in <do_not_translate> must remain in English unless overridden by the target glossary, while all other words MUST be translated into {lang_name}.
4. Semantic Triangulation: Use the Swedish anchor translation and <anchor_glossary_swedish> to disambiguate English terms. Use <developer_comment> only for context.
5. Return ONLY the translated {lang_name} text.

<style_guide>
{style_guide}
</style_guide>

<anchor_glossary_swedish>
{json.dumps(sv_glossary, ensure_ascii=False, indent=2)}
</anchor_glossary_swedish>

<target_glossary_{tag_lang}>
{json.dumps(target_glossary, ensure_ascii=False, indent=2)}
</target_glossary_{tag_lang}>

<do_not_translate>
{json.dumps(target_dnt, ensure_ascii=False, indent=2)}
</do_not_translate>"""


def resolve_input_blob(bucket, explicit_blob):
    if explicit_blob:
        blob = bucket.blob(explicit_blob)
        if not blob.exists():
            raise FileNotFoundError(f"Blob '{explicit_blob}' not found in {bucket.name}")
        return blob
    blobs = [
        b for b in bucket.list_blobs()
        if b.name.endswith(".xlsx") and not b.name.endswith("_completed.xlsx")
    ]
    if not blobs:
        raise FileNotFoundError(f"No input .xlsx file found in bucket {bucket.name}")
    return max(blobs, key=lambda b: b.updated or 0)


def translate_dataframe(df, genai_client, target_langs, max_workers=20, model_name="gemini-2.5-flash"):
    style_guide = load_file(os.path.join(GLOSSARY_DIR, "Translationsupport.md"))
    raw_dnt = load_json(os.path.join(GLOSSARY_DIR, "do_not_translate.json"))
    sv_glossary = load_glossary_for_lang("sv")
    sv_dnt = get_active_dnt(sv_glossary, raw_dnt)
    sys_prompt_anchor = build_anchor_prompt(style_guide, sv_glossary, sv_dnt)

    if "en" in df.columns and "Master" in df.columns:
        df["en"] = df.apply(
            lambda r: r["en"] if str(r["en"]).strip() != "" else r["Master"], axis=1
        )
    elif "Master" in df.columns:
        df["en"] = df["Master"]

    sheet_langs = [
        c.strip().lower()
        for c in df.columns
        if c.strip().lower() in LANG_NAMES and c.strip().lower() not in ("en", "sv")
    ]
    all_target_langs = list(dict.fromkeys(sheet_langs + [l for l in target_langs if l != "sv"]))

    target_prompts = {}
    for lang in all_target_langs:
        t_glossary = load_glossary_for_lang(lang)
        t_dnt = get_active_dnt(t_glossary, raw_dnt)
        target_prompts[lang] = build_target_prompt(
            lang, style_guide, sv_glossary, t_glossary, t_dnt
        )

    df["sv"] = ""
    df["sv"] = df["sv"].astype(object)
    for lang in target_prompts:
        if lang not in df.columns:
            df[lang] = ""
        df[lang] = df[lang].astype(object)

    total_rows = len(df)

    def process_anchor(idx, row):
        src = str(row.get("en", "")).strip() or str(row.get("Master", "")).strip()
        comment = str(row.get("Comment", "")).strip()
        if not is_translatable(src):
            return idx, src
        prompt = (
            f"<source_english_text>\n{src}\n</source_english_text>\n\n"
            f"<developer_comment>\n{comment}\n</developer_comment>"
        )
        raw = call_gemini(genai_client, prompt, sys_prompt_anchor, model_name)
        return idx, validate_translation(src, raw)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_anchor, i, r): i for i, r in df.iterrows()}
        for future in tqdm(
            as_completed(futures), total=total_rows, desc="Pass 1: Swedish Anchor", file=sys.stdout
        ):
            idx, sv_text = future.result()
            df.at[idx, "sv"] = sv_text

    def process_downstream(idx, row):
        src = str(row.get("en", "")).strip() or str(row.get("Master", "")).strip()
        comment = str(row.get("Comment", "")).strip()
        sv_text = str(row.get("sv", "")).strip()
        if not is_translatable(src):
            return idx, {lang: src for lang in target_prompts}
        prompt = (
            f"<source_english_text>\n{src}\n</source_english_text>\n\n"
            f"<anchor_swedish_translation>\n{sv_text}\n</anchor_swedish_translation>\n\n"
            f"<developer_comment>\n{comment}\n</developer_comment>"
        )
        results = {}
        for lang, sys_prompt in target_prompts.items():
            raw = call_gemini(genai_client, prompt, sys_prompt, model_name)
            results[lang] = validate_translation(src, raw)
        return idx, results

    if target_prompts:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_downstream, i, r): i for i, r in df.iterrows()}
            for future in tqdm(
                as_completed(futures), total=total_rows, desc="Pass 2: Target Langs", file=sys.stdout
            ):
                idx, lang_map = future.result()
                for lang, val in lang_map.items():
                    df.at[idx, lang] = val

    return df


def main():
    input_bucket_name = os.environ.get("INPUT_BUCKET")
    output_bucket_name = os.environ.get("OUTPUT_BUCKET")
    input_blob_name = os.environ.get("INPUT_BLOB", "")
    target_langs = [
        lang.strip().lower()
        for lang in os.environ.get("TARGET_LANGS", "es,fr,nl").split(",")
        if lang.strip()
    ]
    max_workers = int(os.environ.get("MAX_WORKERS", "20"))
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    if not input_bucket_name or not output_bucket_name:
        raise ValueError("INPUT_BUCKET and OUTPUT_BUCKET environment variables are required.")

    storage_client = storage.Client()
    genai_client = genai.Client(http_options={"api_version": "v1beta"})

    in_bucket = storage_client.bucket(input_bucket_name)
    out_bucket = storage_client.bucket(output_bucket_name)
    blob = resolve_input_blob(in_bucket, input_blob_name)

    with tempfile.TemporaryDirectory() as tmpdir:
        local_in = os.path.join(tmpdir, os.path.basename(blob.name))
        blob.download_to_filename(local_in)
        print(f"Downloaded gs://{input_bucket_name}/{blob.name}")

        xl = pd.ExcelFile(local_in)
        sheet_name = xl.sheet_names[0]
        df_check = pd.read_excel(local_in, sheet_name=sheet_name, header=0, keep_default_na=False)
        if any(col in df_check.columns for col in ["ID", "en", "Master"]):
            df = df_check
        else:
            df = pd.read_excel(local_in, sheet_name=sheet_name, header=1, keep_default_na=False)

        df = translate_dataframe(df, genai_client, target_langs, max_workers, model_name)

        out_name = re.sub(r"\.xlsx$", "_completed.xlsx", blob.name, flags=re.IGNORECASE)
        local_out = os.path.join(tmpdir, os.path.basename(out_name))
        with pd.ExcelWriter(local_out) as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

        out_blob = out_bucket.blob(out_name)
        out_blob.upload_from_filename(local_out)
        print(f"Uploaded gs://{output_bucket_name}/{out_name}")


if __name__ == "__main__":
    main()
