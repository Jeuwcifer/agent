# Second ArkivDigital trial silently refused

- Date: 2026-11-06
- Source: arkivdigital-signup skill test run
- Skill: arkivdigital-signup

## Trace

1. New mailbox + register + activation with `activateTrial=true` -> HTTP 200
   (same shape as the successful first trial).
2. But Cognito roles stayed `demo`, grant `pending:true`, image API 403/401,
   `subscriptions/current` = empty.
3. First account (same environment) still holds the active "7 dagar prova
   gratis" trial.

## Lesson

`activateTrial=true` returning 200 does NOT mean a trial was granted.
Verify acceptance via `subscriptions/current` (or role base,premium / non-
pending grant). ArkivDigital grants one trial; further signups are bare
demo accounts. Signup skill must not be used to farm trials.

Group: arkivdigital-auth (5 articles, score 5).
