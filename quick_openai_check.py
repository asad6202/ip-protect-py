#!/usr/bin/env python3
"""
Quick OpenAI API key checker.
Usage: python quick_openai_check.py
Reads OPENAI_API_KEY from .env or environment and makes a tiny test call.
"""

import os
from dotenv import load_dotenv, dotenv_values

def mask(key: str) -> str:
    if not key:
        return "<missing>"
    if len(key) <= 8:
        return "*" * len(key)
    return key[:6] + "..." + key[-4:]

def main() -> None:
    # Load .env with override to prefer .env over existing env vars
    load_dotenv(override=True)
    api_key = os.getenv("OPENAI_API_KEY")
    file_vars = {}
    try:
        file_vars = dotenv_values(".env") or {}
    except Exception:
        file_vars = {}
    if not api_key:
        print("❌ OPENAI_API_KEY not found. Create a .env with OPENAI_API_KEY=sk-... or set the env var.")
        return
    print(f"🔑 Using OPENAI_API_KEY (effective): {mask(api_key)}")
    file_key = file_vars.get("OPENAI_API_KEY")
    if file_key:
        print(f"📄 .env OPENAI_API_KEY: {mask(file_key)}")
        if file_key != api_key:
            print("⚠️  Effective key differs from .env. A system/user env var may be overriding it.")
            print("   On PowerShell, check with: $env:OPENAI_API_KEY")
            print("   Clear overrides with:")
            print("   [Environment]::SetEnvironmentVariable(\"OPENAI_API_KEY\", $null, \"User\")")
            print("   [Environment]::SetEnvironmentVariable(\"OPENAI_API_KEY\", $null, \"Machine\") (admin)")

    try:
        from openai import OpenAI
    except Exception as e:
        print(f"❌ openai package not installed: {e}\n   Run: pip install openai python-dotenv")
        return

    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Reply with exactly: OK"},
            ],
            max_tokens=3,
            temperature=0,
        )
        text = (resp.choices[0].message.content or "").strip()
        print("✅ API call succeeded.")
        print(f"↳ Response: {text}")
    except Exception as e:
        msg = str(e)
        print("❌ API call failed.")
        print(f"↳ Error: {msg}")
        if "incorrect api key" in msg.lower() or "invalid_api_key" in msg.lower():
            print("Hint: Key is invalid. Re-copy from https://platform.openai.com/api-keys")
        elif "insufficient_quota" in msg.lower() or "billing" in msg.lower():
            print("Hint: Add billing/credits: https://platform.openai.com/account/billing")
        elif "model" in msg.lower():
            print("Hint: Try a different model or check access. e.g., gpt-4o-mini")
        elif "timeout" in msg.lower() or "connection" in msg.lower():
            print("Hint: Check your internet / firewall and try again.")


if __name__ == "__main__":
    main()


