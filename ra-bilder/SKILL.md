---
name: ra-bilder
description: Downloads full-resolution record images from Riksarkivet (Swedish National Archives) via its public IIIF server, free and without an account. Triggers on requests like "get images from Riksarkivet", "download church book pages SVAR", "RA bildid C0072904", "fetch digitized volume images", "husförhörslängd bilder", or when ArkivDigital is unavailable/refused and the records exist at Riksarkivet.
---

# ra-bilder

Riksarkivet serves every digitized page as IIIF at
`https://lbiiif.riksarkivet.se/arkis!<bildid>_<page>/full/max/0/default.jpg`
(full resolution JPEG, typically ~3500×2500 px, no watermark). Free,
no account. Only gate = Altcha checkbox sets one cookie.

Fetcher script (stdlib only): `/home/user/Documents/ra_bilder/ra_bild.py`

## Steps

1. **Find the volume id (bildid).** Search
   https://sok.riksarkivet.se/digitala-forskarsalen by parish, open
   archive → series → volume. Digitized volumes show
   `Reproducerad på: …/<C-nummer>` — that C-number is the bildid.
   Direct viewer check: `https://sok.riksarkivet.se/bildvisning/<id>`.

2. **Pass Altcha once, grab cookies.** With agent-browser:
   open the viewer URL, click the "Jag är inte en robot" checkbox,
   wait 3 s, then run `agent-browser cookies`. Needed: the
   `altcha_verified=…` cookie (ASP.NET_SessionId optional).
   Cookies live for the browser session; refetch if IIIF returns 403.

3. **Fetch pages.**

```
cd /home/user/Documents/ra_bilder
```

```
python3 ra_bild.py C0072904 --cookie "$CK" --pages 1-10
```

`$CK` = the cookie string. Omit `--pages` for the whole volume.
Script prints page count from the IIIF manifest, saves
`<id>/<id>_pNNN.jpg` (1 full-res JPEG per page), 1 s sleep between
pages — keep that politeness gap; do not parallelize.

## Verification

Manifest (also proves id + cookie validity):

```
curl -s -A "$UA" -b "$CK" \
  https://lbiiif.riksarkivet.se/arkis!C0072904/manifest
```

200 + JSON with `items` = good. 403 = refetch cookies (step 2).
Image sanity: `file <img>.jpg` must say real dimensions, not HTML.

## Limits

- Some volumes are restricted (privacy, deposit terms): viewer then
  requires login with Swedish e-id. No workaround — pick another
  volume or another archive holding the same records.
- Curl without the altcha cookie gets 403 even with a browser UA.
- Manifest is IIIF Presentation 3: pages under `items`, URL at
  `items[i].items[0].items[0].body.id`.
- ArkivDigital ids (v-numbers, `v<id>.b<n>`) do NOT work here. This
  is Riksarkivet only.
