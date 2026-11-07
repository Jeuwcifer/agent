# ArkivDigital tiles2 WAF blocks datacenter IPs

- Date: 2026-11-06
- Source: live session, arkivdigital-bilder skill
- Skill: arkivdigital-bilder

## Trace

1. Trial account fully active (premium role, subscription 200, thumbnails
   and images metadata 200 from API host).
2. Every request to `tiles2.arkivdigital.se` (image CDN, signed URLs)
   returned CloudFront "403 ERROR / Request blocked" — from curl AND from
   real Chromium (proper UA, headers, Referer, Bearer).
3. Host names tiles/tiles3 do not resolve. So block is IP-based (server
   egress), not UA/TLS/cookie.

## Lesson

- API host (api.production.arkivdigital.se) and tiles CDN have separate
  WAF policies. "API works but images 403" from a server = move image
  fetching to a residential connection; do not burn time on header games.
- Clean full-res images come from tiles_url (`<base><z>/<x>_<y>.jpeg`);
  the `download_tile` endpoint is a watermarked screenshot re-encode.

Group: arkivdigital-auth (4 articles, score 4).

## Correction (2026-11-06 later)

Theory WRONG. Tiles are not IP-blocked. Root cause: downloader probed
`.jpeg` (DZI format is `.jpg`) and probe loop bailed on first miss; the
earlier manual probes also used expired signed URLs and wrong paths, and
CloudFront returns the same generic 403 page for expired signatures and
root path. Verified from this same server: `<tiles_url>10/0_0.jpg` -> 200,
`12/0_0.jpg` -> 200 (full-res level), and a stitched 6000x4000 JPEG page
downloaded successfully. Lesson: a WAF-looking 403 page can mask wrong
path/extension/expiry — verify the exact URL scheme from app source
before blaming network.

## Rate cap measured (2026-11-06 later)

tiles2 throttle band: ~95 rps cold tiles = clean (300/300 200s); 250 rps
burst -> 28x403 + latency collapse (effective 64 rps) and a TEMPORARY IP
block (fresh signed URLs 403 for minutes+). Run rate pinned at 66 rps =
70% of confirmed-safe 95. Pacer in skane_download.py (--rps). Never
probe above ~150 rps on a live account: the block also halts legit work.

## Sustained-volume throttle (2026-11-06 later)

Block re-triggers after ~2400 tiles (~100 pages) even at ~6 rps average:
bursty 66-rps page bursts count. Fix in skane_download.py: 403 = soft
signal (backoff 60-300s, refetch signed URLs, auto-halve rate to floor
5 rps, retry 12x, then next cycle). Defaults 8 workers / 30 rps start.
