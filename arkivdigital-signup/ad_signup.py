#!/usr/bin/env python3
"""ArkivDigital account signup + app-token refresh. Stdlib only.

Commands:
  signup   create mailbox, register ArkivDigital account with 7-day
           trial, activate via email link, store account + app token
  token    refresh app token for the stored account (auto-activates
           pending sessions)

State:  ~/.arkivdigital_account.json  (email, password)
Token:  ~/Documents/ad_bilder/.ad_token (shared with ad_bild.py)
"""
import argparse
import json
import random
import re
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.production.arkivdigital.se"
BIZ = "https://biz.production.arkivdigital.se/api/pu/v1"
COGNITO = "https://cognito-idp.eu-west-1.amazonaws.com/"
COG_CLIENT = "4n3t2ajq9koou6l2l65c7jdcg2"
ORIGIN = "https://www.arkivdigital.net"
REGISTER_REFERER = ORIGIN + "/account/new"
ACCOUNT_FILE = Path.home() / ".arkivdigital_account.json"
TOKEN_FILE = Path.home() / "Documents" / "ad_bilder" / ".ad_token"
UA = "ad-signup/1.0"
VERIFY_AID = "v19085"  # any valid volume for access check


def http(url, method="GET", body=None, headers=None, raw=False):
    req = urllib.request.Request(url, data=body, method=method,
                                 headers=dict({"User-Agent": UA}, **(headers or {})))
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
            if raw or not data.strip():
                return data, r.status
            try:
                return json.loads(data), r.status
            except json.JSONDecodeError:
                return data[:300], r.status
    except urllib.error.HTTPError as e:
        msg = e.read()[:200]
        raise SystemExit(f"HTTP {e.code} for {url}: {msg!r}")


def mailtm_create():
    doms, _ = http("https://api.mail.tm/domains")
    domain = doms["hydra:member"][0]["domain"]
    user = "adtrial" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    addr = f"{user}@{domain}"
    pw = "AdTrial-" + "".join(random.choices(string.ascii_letters + string.digits, k=10))
    http("https://api.mail.tm/accounts", "POST",
         json.dumps({"address": addr, "password": pw}).encode(),
         {"Content-Type": "application/json"})
    tok, _ = http("https://api.mail.tm/token", "POST",
                  json.dumps({"address": addr, "password": pw}).encode(),
                  {"Content-Type": "application/json"})
    print(f"mailbox: {addr}")
    return addr, pw, tok["token"]


def ad_register(addr, password, tries=3):
    body = json.dumps({"email": addr, "name": "AD User", "password": password,
                       "locale": "sv", "newsletter": False}).encode()
    hdr = {"Content-Type": "application/json", "Origin": ORIGIN,
           "Referer": REGISTER_REFERER}
    for t in range(tries):
        req = urllib.request.Request(BIZ + "/user_registrations", data=body,
                                     method="POST",
                                     headers=dict({"User-Agent": UA}, **hdr))
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                print("register:", r.status)
                return
        except urllib.error.HTTPError as e:
            if e.code == 403 and t < tries - 1:
                print("register 403 (rate limit), waiting 90 s")
                time.sleep(90)
                continue
            raise SystemExit(f"register failed: HTTP {e.code} {e.read()[:200]!r}")
    raise SystemExit("register failed after retries")


def mailtm_wait_key(mt_token, minutes=5):
    hdr = {"Authorization": "Bearer " + mt_token}
    for _ in range(minutes * 6):
        time.sleep(10)
        msgs, _ = http("https://api.mail.tm/messages", headers=hdr)
        for m in msgs.get("hydra:member", []):
            full, _ = http("https://api.mail.tm/messages/" + m["id"], headers=hdr)
            text = str(full.get("text", "")) + str(full.get("html", ""))
            hit = re.search(r"activation/([A-Za-z0-9]+)", text)
            if hit:
                print("activation key:", hit.group(1))
                return hit.group(1)
    raise SystemExit("no activation email within timeout")


def ad_activate(key, password):
    hdr = {"Content-Type": "application/json", "Origin": ORIGIN,
           "Referer": ORIGIN + "/account/newactivation/" + key}
    info, st = http(f"{BIZ}/user_registrations/inactive?key={key}&locale=sv",
                    headers=hdr)
    print("inactive check:", st, info.get("email"))
    body = json.dumps({"password": password,
                       "password_confirmation": password}).encode()
    _, st = http(f"{BIZ}/user_registrations/activate?key={key}&activateTrial=true",
                 "PUT", body, hdr)
    print("activate:", st, "(trial link: activateTrial=true)")


def cognito_id_token(user, password):
    body = json.dumps({"AuthFlow": "USER_PASSWORD_AUTH", "ClientId": COG_CLIENT,
                       "AuthParameters": {"USERNAME": user, "PASSWORD": password}}).encode()
    hdr = {"Content-Type": "application/x-amz-json-1.1",
           "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth"}
    res, _ = http(COGNITO, "POST", body, hdr)
    return res["AuthenticationResult"]["IdToken"]


def app_token(user, password, activate_pending=True):
    body = urllib.parse.urlencode(
        {"grant_type": "password", "username": user, "password": password}).encode()
    tok, _ = http(API + "/api/v1/tokens", "POST", body,
                  {"Content-Type": "application/x-www-form-urlencoded"})
    if not tok.get("access_token"):
        raise SystemExit(f"no access_token: {tok}")
    token = tok["access_token"]
    if tok.get("pending"):
        if not activate_pending:
            raise SystemExit("token pending (other session active)")
        idt = cognito_id_token(user, password)
        body2 = urllib.parse.urlencode({"adtree_token": idt}).encode()
        _, st = http(API + "/api/v1/tokens/activate_pending", "PATCH", body2,
                     {"Authorization": "Bearer " + token,
                      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
        print("pending session activated:", st)
    # verify (non-fatal: token is valid even if the verify probe hiccups)
    try:
        _, st = http(f"{API}/api/v1/volume_versions?aid={VERIFY_AID}",
                     headers={"Authorization": "Bearer " + token})
        print("access verified:", st)
    except SystemExit as e:
        print("verify skipped:", e)
    return token


def save_account(addr, password):
    ACCOUNT_FILE.write_text(json.dumps({"email": addr, "password": password}))
    ACCOUNT_FILE.chmod(0o600)
    print("account saved:", ACCOUNT_FILE)


def save_token(token):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token)
    print("token saved:", TOKEN_FILE)


def load_account():
    if not ACCOUNT_FILE.exists():
        sys.exit(f"No account at {ACCOUNT_FILE}. Run: python3 ad_signup.py signup")
    return json.loads(ACCOUNT_FILE.read_text())


def cmd_signup(_args):
    addr, pw, mt = mailtm_create()
    save_account(addr, pw)
    ad_register(addr, pw)
    key = mailtm_wait_key(mt)
    ad_activate(key, pw)
    save_token(app_token(addr, pw))
    print("signup complete. Trial granted only if no other trial exists")
    print("(else role demo, no images). Verify: volume_versions 200 = trial OK")


def cmd_token(_args):
    import fcntl
    lock = open("/tmp/ad_signup_token.lock", "w")
    fcntl.flock(lock, fcntl.LOCK_EX)  # serialize refreshes across processes
    acc = load_account()
    save_token(app_token(acc["email"], acc["password"]))
    print("token refreshed for", acc["email"])


def cmd_set_account(args):
    import getpass
    email = args.email or input("ArkivDigital email: ").strip()
    pw = args.password or getpass.getpass("password: ")
    save_account(email, pw)
    print("account saved. Next: python3 ad_signup.py token")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cmd", choices=["signup", "token", "set-account"])
    p.add_argument("-u", "--email", help="account email (set-account)")
    p.add_argument("-p", "--password", help="account password (set-account)")
    a = p.parse_args()
    {"signup": cmd_signup, "token": cmd_token,
     "set-account": cmd_set_account}[a.cmd](a)


if __name__ == "__main__":
    main()
