# ArkivDigital demo role = no image access, regardless of activation

- Date: 2026-11-06
- Source: live session, arkivdigital-bilder skill
- Skill: arkivdigital-bilder

## Trace

1. Activation email re-sent; ArkivDigital replied "you already have an
   account, just log in" — activation was never the blocker.
2. www restricted API (`/api/ru/v1/profile`, Cognito access token + x-ad-*
   headers) works: user 329484, `email_verified: true`.
3. Cognito idToken payload: `custom:roles: demo`, `custom:concurrent_sessions: 1`.
4. `/subscriptions/current` = empty. Products catalog (public): only paid
   subscriptions (395 SEK/month, 2195 SEK/year), no free trial product.
5. Password grant always returns `pending: true`, `id_token: null` for demo
   accounts; every image API call 401s. Browser app login error was a CORS/WAF
   artifact of headless browsers, not real login state.

## Lesson

- `pending: true` on `/api/v1/tokens` = account has no active subscription
  (demo role), NOT unactivated email.
- Diagnose account state via Cognito idToken claims (`custom:roles`) +
  `/api/ru/v1/subscriptions/current` before blaming activation.
- Restricted API auth: `Authorization: Bearer <Cognito ACCESS token>` plus
  headers `x-ad-adbusiness-user-id` (claim `custom:adbusiness_user_id`),
  `x-ad-email` (claim `preferred_username`), `x-ad-locale`.
- No free image tier exists on ArkivDigital. Same church records: use
  ra-bilder (Riksarkivet IIIF, free).

Group: arkivdigital-auth (3 articles, score 3).
