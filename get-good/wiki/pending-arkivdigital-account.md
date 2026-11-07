# Pending ArkivDigital account blocks API despite token issuance

- Date: 2026-11-06
- Source: live debugging, session with user account obin.dansandejude@gmail.com
- Skill: arkivdigital-bilder

## Trace

1. `POST /api/v1/tokens` (password grant) returned `access_token` (24 chars),
   `pending: true`, `id_token: null`, `organization: false`, `expires_at` +30 d.
2. All API calls with that Bearer token → 401 empty body
   (thumbnails, counties).
3. `PATCH /api/v1/tokens/activate_pending` with empty `adtree_token` → 404
   Rails page. Route needs a real `id_token`, which pending accounts lack.
4. Web login (app.arkivdigital.se, agent-browser) → "Invalid login
   credentials". Ground truth: account exists, not email-activated.

## Lesson

Password-grant token issuance does NOT mean credentials fully valid or account
usable. Check `pending` and `id_token` fields before burning retries:
- `pending: true` + `id_token: null` → stop, tell user to click activation
  email. Retries and activate_pending cannot help.
- Web login error text is the reliable ground truth for account state.

Group: none yet (first article).

## Correction (2026-11-06 later)

The "activate_pending 404" in this trace was NOT a dead route: probes used
POST; the route is PATCH. POST /api/v1/tokens/activate_pending -> 404,
PATCH with `adtree_token=<Cognito IdToken>` -> 200, token becomes active.
`pending:true` on grant = single-session device-switch case, not only
"unactivated email". Verified with the trial account
(pending:true -> PATCH -> pending:false -> API 200).
