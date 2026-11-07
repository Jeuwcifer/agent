# ArkivDigital auth flow

Group page. Connected articles: 5. Priority score: 5.

## Articles

- [Pending ArkivDigital account blocks API despite token issuance](pending-arkivdigital-account.md)
- [Resend ArkivDigital activation email — no UI, direct biz API POST](arkivdigital-resend-activation.md)
- [ArkivDigital demo role = no image access, regardless of activation](arkivdigital-demo-role.md)
- [ArkivDigital tiles2 WAF blocks datacenter IPs](arkivdigital-tiles2-waf.md)
- [Second ArkivDigital trial silently refused](arkivdigital-second-trial-refused.md)

## Synthesis

Account state, activation, and email flows for ArkivDigital live in the
www signup SPA + biz API + AWS Cognito, not in the app.arkivdigital.se
viewer. Debug order: password grant → check `pending`/`id_token` →
decode Cognito idToken for `custom:roles` → check
`/api/ru/v1/subscriptions/current` → if role demo and no subscription,
images are paywalled; redirect to ra-bilder instead of more auth digging.
