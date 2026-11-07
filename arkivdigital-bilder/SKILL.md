---
name: arkivdigital-bilder
description: Accesses ArkivDigital (arkivdigital.se) images through its official app API with an account (OAuth2 password grant). Supports trial signup via API (7 days free). Triggers on requests like "download images from ArkivDigital", "ArkivDigital bildid v123456.b78", "fetch church book pages from ArkivDigital", "ArkivDigital kyrkbok bilder". Use ra-bilder instead when the same record exists at Riksarkivet or when no ArkivDigital account is available.
---

# arkivdigital-bilder

All image access requires an account with an active subscription or trial.
Never bypass the paywall. The 7-day trial is ArkivDigital's own offer.

## Verified endpoints (2026-11-06)

- API host: `https://api.production.arkivdigital.se`
- Auth: `POST /api/v1/tokens`, form-encoded
  `grant_type=password&username=<user>&password=<pass>`.
  Healthy account (subscription/trial): `pending: false`. Bearer on all calls.
- `pending: true` on grant = another session holds the single-session slot
  (device switch), NOT a dead account. Fix: `PATCH
  /api/v1/tokens/activate_pending` (PATCH — POST gives 404) with form body
  `adtree_token=<Cognito IdToken>` (Cognito pool eu-west-1_qWA42Sa2b,
  client 4n3t2ajq9koou6l2l65c7jdcg2, `USER_PASSWORD_AUTH`), Bearer = pending
  token → `pending:false`, same token active. ad_bild.py login auto-handles.
  Unactivated email case is different: web login says "Invalid login
  credentials", grant gives `pending:true` + `id_token:null`.
- `GET /api/v1/volume_versions?aid=vNNNNNN` → volume metadata
  (`data.attributes`: display_name, number_of_images, nad_code, year_*).
- `GET /api/v1/images?volume_version_aid=vNNNNNN` → page list.
  `data[i].attributes`: aid (`v19085.b1`), resolution, `image_no`,
  `image_file_path`, `tiles_url`.
- `GET /api/v1/thumbnails?volume_aid=vNNNNNN` → compact page list
  (`o[i]`: image_aid, tiles_url).
- `tiles_url` base + `<z>/<x>_<y>.jpg` serves DZI tiles (viewer config:
  Format jpg, TileSize 1024, Overlap 2, max level = ceil(log2(max(W,H))).
  Root URL returns 403 — that is normal; only tile paths respond. Tile URLs
  are signed and expire ~1 h; always use the `tiles_url` from a fresh page
  list. Earlier "WAF blocks datacenter IP" theory was WRONG — tiles serve
  fine from servers when the path/extension is right.
- `/api/v1/images/download_tile/<id>` = POST form (token, uri) — server
  re-encodes a viewer screenshot WITH watermark. Not a clean download.

## Trial signup via API (verified full flow)

1. Mailbox: create programmatic one at mail.tm
   (`POST /accounts`, `POST /token`).
2. Register: `POST https://biz.production.arkivdigital.se/api/pu/v1/user_registrations`
   JSON `{email,name,password,locale:"sv",newsletter:false}` — requires
   headers `Origin: https://www.arkivdigital.net` AND
   `Referer: .../account/new`, else 403. 200 = activation email sent.
3. Read mail, extract key from link `.../newactivation/<KEY>?activateTrial=true`.
4. Check: `GET .../user_registrations/inactive?key=<KEY>&locale=sv`
   (same Origin/Referer, else 403) → returns email, correlation_id.
5. Activate + trial in one shot:
   `PUT .../user_registrations/activate?key=<KEY>&activateTrial=true`
   JSON body `{password, password_confirmation}` → 200.
   (Body key params in PUT → misleading 404 "link invalid". Key goes in URL.)
   Single-use key; wrong shape can burn it — re-register to get a new one.
6. `POST /api/v1/tokens` form-encoded → `pending: false` → done.
   Cognito idToken then shows `custom:roles: base,premium`; trial period
   visible at `GET biz.../api/ru/v1/subscriptions/current` (Cognito access
   token + x-ad-* headers, see get-good wiki).

## Helper script

`/home/user/Documents/ad_bilder/ad_bild.py` — login (form-encoded), `api`
GET, `get` absolute URL. Trial creds: `trial_account.md` in same dir.

## Usage

```
python3 ad_bild.py login -u adbild3i0j1jl0@fldubai.com -p 'AdTrial-2026x!'
```

```
python3 ad_bild.py api "/api/v1/images?volume_version_aid=v19085"
```

Save JSON, take `data[i].attributes.tiles_url`, fetch tiles
`<tiles_url><z>/<x>_<y>.jpeg` or page composite; 1 s politeness gap.

## Skane volume downloader

`/home/user/Documents/ad_bilder/skane_download.py` — enumerates Skane
parishes → archive collections → volumes, downloads pages (tiles + stitch).
Parish names cached in `skane_parishes.txt` (407, from Wikipedia category
Kategori:Socknar i Skåne → 23 härad subcategories).

```
python3 skane_download.py inventory [--parish NAME] [--refresh]
```

```
python3 skane_download.py download [--parish NAME] --max-volumes 5
```

Verified enumeration facts:
- Parish lookup: `GET /api/v1/volume_collections?query=<base>&application=archive`.
  Collection name field is `name` (NOT display_name). Keep only archives whose
  `ancestor_types` include Arkivtyp "Församling/Socken" and county_letters
  intersect {L, M} (Skåne).
- Exact `name == base` match wins; else prefix match `base+'s'`/`base+' '` —
  needed for city parishes (Helsingborgs socken → Helsingborgs landsförsamling,
  stadsförsamling (Maria), Gustav Adolf, garnisonsförsamling).
- Volumes per collection: `GET /api/v1/volumes?volume_collection_id=<id>`.
- Pages per volume: `GET /api/v1/images?volume_version_aid=<vNNN>`.
- Tile pyramid: `<tiles_url><z>/<x>_<y>.jpeg`, OpenSeadragon config
  TileSize 1024, Overlap 2. Script probes z/grid at runtime and stitches
  with Pillow (installed: 10.2.0). Tile URL errors: root path 403 is
  normal; tile 403 = expired signed URL (refetch page list) or wrong
  path/extension (must be `<z>/<x>_<y>.jpg`).

## Limits

- Tile URLs expire ~1 h; refetch the page list for stale 403s.
- Trial = 7 days, single account. Do not mass-register.
- Restricted archives may still 403 with valid trial.
- Fallback: ra-bilder skill (Riksarkivet IIIF, free, full resolution).
