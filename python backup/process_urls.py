import sys
import urllib.request
import urllib.error

results = []
try:
    with open('urls.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    print("urls.txt not found")
    sys.exit(1)

for i, url in enumerate(urls, 1):
    try:
        response = urllib.request.urlopen(url, timeout=10)
        status = response.getcode()
        results.append(f"{i}. {url} -> OK (status {status})")
    except Exception as e:
        results.append(f"{i}. {url} -> FAILED ({str(e)})")

with open('response.txt', 'w') as f:
    f.write("Processing Results:\n")
    f.write("==================\n")
    f.write('\n'.join(results))
    f.write(f"\n\nTotal URLs: {len(urls)}")
