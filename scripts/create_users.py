#!/usr/bin/env python3
"""快速创建用户脚本。"""
import json, time, urllib.request, os

BASE_URL = "http://localhost:8080"
users = []

for i in range(1, 26):
    email = f"user_{i:03d}@example.com"
    password = "test123456"
    
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/register",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get("code") == 0:
            token = data["data"]["access_token"]
            users.append({"email": email, "token": token, "user_id": None})
            print(f"[{i}/25] OK {email}")
        else:
            msg = data.get('message', '')
            if '429' in str(msg) or '频繁' in str(msg):
                print(f"[{i}/25] 429, waiting 15s...")
                time.sleep(15)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                if data.get("code") == 0:
                    token = data["data"]["access_token"]
                    users.append({"email": email, "token": token, "user_id": None})
                    print(f"[{i}/25] OK {email} (retry)")
                else:
                    print(f"[{i}/25] FAIL {email}: {data.get('message')} after retry")
            else:
                print(f"[{i}/25] FAIL {email}: {msg}")
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"[{i}/25] 429, waiting 15s...")
            time.sleep(15)
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                if data.get("code") == 0:
                    token = data["data"]["access_token"]
                    users.append({"email": email, "token": token, "user_id": None})
                    print(f"[{i}/25] OK {email} (retry)")
            except Exception as e2:
                print(f"[{i}/25] FAIL {email}: retry error {e2}")
        else:
            print(f"[{i}/25] FAIL {email}: HTTP {e.code}")
    except Exception as e:
        print(f"[{i}/25] FAIL {email}: {e}")
    
    time.sleep(13)

os.makedirs("/Users/finley/01_Projects/Python_AI/snaptrip/.import_work", exist_ok=True)
with open("/Users/finley/01_Projects/Python_AI/snaptrip/.import_work/users.json", "w") as f:
    json.dump(users, f, ensure_ascii=False, indent=2)

print(f"\nDone: {len(users)}/25 users created")
