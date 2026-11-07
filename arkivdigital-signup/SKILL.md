---
name: arkivdigital-signup
description: Creates ArkivDigital accounts via their official signup API (free 7-day trial included) and refreshes app API tokens on demand. Triggers on "sign up ArkivDigital", "create ArkivDigital account", "new trial account", "refresh ArkivDigital token", "token expired ad_bild", or when arkivdigital-bilder reports 401/pending login issues.
---

# arkivdigital-signup

Automates the verified signup flow for ArkivDigital and keeps a working
API token. Official endpoints only; never bypass the paywall — the 7-day
trial is ArkivDigital's own offer from their activation link.

Script: `ad_signup.py` (this directory, stdlib only).

State:
- `~/.arkivdigital_account.json` — account email + password
- `~/Documents/ad_bilder/.ad_token` — app token (shared with ad_bild.py
  and skane_download.py)

## Commands

```
python3 ad_signup.py signup
```

```
python3 ad_signup.py token
```

## What `signup` does (verified flow)

1. Create disposable mailbox at mail.tm (API, no captcha).
2. Register: `POST biz.production.arkivdigital.se/api/pu/v1/user_registrations`
   JSON `{email,name,password,locale:"sv",newsletter:false}` — requires
   headers `Origin: https://www.arkivdigital.net` AND
   `Referer: .../account/new`, else 403. 200 = activation email sent.
   Rate-limited per IP: on 403 wait 90 s and retry (max 3).
3. Poll mailbox for mail, extract key from link
   `.../newactivation/<KEY>?activateTrial=true`.
4. `GET .../user_registrations/inactive?key=<KEY>&locale=sv` (same headers)
   — validates key, returns email + correlation_id.
5. `PUT .../user_registrations/activate?key=<KEY>&activateTrial=true`
   JSON `{password, password_confirmation}` → account active AND
   "7 dagar prova gratis" subscription created. Key goes in the URL
   (body key params cause misleading 404). Key is single-use.
6. Get app token (`POST /api/v1/tokens`, form-encoded), auto-activate
   pending session if needed, verify access with one API call.

## What `token` does

1. `POST /api/v1/tokens` form-encoded with stored credentials.
2. If response has `pending: true` (another session holds the single
   session slot): `PATCH /api/v1/tokens/activate_pending` with form body
   `adtree_token=<Cognito IdToken>` (Cognito pool eu-west-1_qWA42Sa2b,
   client 4n3t2ajq9koou6l2l65c7jdcg2, `USER_PASSWORD_AUTH`), Bearer =
   pending token. PATCH — POST returns 404.
3. Write token to shared cache, verify with `GET /api/v1/volume_versions`.

## Limits

- One trial per person per ArkivDigital terms. VERIFIED: a second account
  registered from the same environment activated fine but stayed role
  `demo` with zero subscriptions — `activateTrial=true` silently granted
  no trial while another trial is active. `token` refreshes the existing
  account; only run `signup` when the old trial expired or the account is
  unusable. Never mass-create accounts.
- Activation keys are single-use; a wrong-shape activate call burns the
  key (rerun `signup` for a new one).
- Token lifetime ~30 days; `token` reissues on demand.
- Downloading page images is arkivdigital-bilder / skane_download.py
  territory — this skill only does accounts and tokens.
