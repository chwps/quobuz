#!/usr/bin/env python3
"""Test bundle extraction patterns."""
import re

with open('/tmp/bundle.js', 'r') as f:
    js = f.read()

print(f'Bundle size: {len(js)} chars')

# Test pattern 1: qobuz-dl production pattern
match = re.search(r'production:\{api:\{appId:"(\d{9})",appSecret:"(\w{32})"', js)
if match:
    print(f'Pattern 1 MATCH: app_id={match.group(1)}, app_secret={match.group(2)}')
else:
    print('Pattern 1: no match')

# Test pattern 2: app_id
match = re.search(r'"app_id"\s*:\s*"(\d+)"', js)
if match:
    print(f'Pattern 2: app_id={match.group(1)}')
else:
    print('Pattern 2: no match')

# Test pattern 3: authSeeds
seed_match = re.search(r'authSeeds:\s*\[([^\]]+)\]', js)
if seed_match:
    seeds_str = seed_match.group(1)
    seed_matches = re.findall(r'"([^"]+)"', seeds_str)
    print(f'Pattern 4 (authSeeds): found {len(seed_matches)} seeds: {seed_matches[:3]}...')
else:
    print('Pattern 4 (authSeeds): no match')

# Search for common patterns in first 500k chars
print()
print('--- Searching for app_id patterns in bundle ---')
for m in re.finditer(r'app[_Ii]d[":\s,]+\s*["\x27](\d{4,})["\x27', js[:500000]):
    print(f'  Found: {m.group(0)[:60]}')

for m in re.finditer(r'app[_Ss]ecret[":\s,]+\s*["\x27]([a-zA-Z0-9]{10,})["\x27', js[:500000]):
    print(f'  Secret: {m.group(0)[:60]}')
