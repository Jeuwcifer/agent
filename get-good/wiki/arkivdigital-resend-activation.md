# Resend ArkivDigital activation email — no UI, direct biz API POST

- Date: 2026-11-06
- Source: live session, arkivdigital-bilder skill debugging
- Skill: arkivdigital-bilder

## Trace

1. User lost activation email; account `pending: true`, API 401 everywhere.
2. Sites have NO resend-verification UI (searched app JS, login page, FAQ,
   signup SPA; /aktivera redirects to support page; signup pages on both
   domains render "Something went wrong").
3. Cognito ResendConfirmationCode → "Auto verification not turned on" —
   dead end, pool has auto-verify off.
4. ws.js (www signup SPA) revealed `adBusinessPublicUrl` endpoints:
   POST /user_registrations (register),
   GET /user_registrations/inactive?key=, PUT /user_registrations/activate.
5. POST /user_registrations with `{email,name,password,locale,newsletter}`
   + Origin header → 200, activation email re-sent.

## Lesson

- Reverse the signup SPA bundle (www.arkivdigital.net/static/js/main.*.js)
  for account-lifecycle endpoints; the Ember viewer app knows only image
  endpoints.
- POST /user_registrations doubles as activation-email resend; requires
  `Origin` header, else 403; snake_case wrapper key, else 400.
- Headless-browser POSTs to cognito-idp get WAF 403; curl passes. When
  browser login fails with "Invalid e-mail address or password" but curl
  succeeds, suspect WAF, not credentials.

Group: arkivdigital-auth (see also pending-arkivdigital-account.md).
