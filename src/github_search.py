import os, requests
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN","")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

def search_code(deprecated_term, pages=2):
    q = f"{deprecated_term}+in:file"
    url = "https://api.github.com/search/code"
    params = {"q":q,"per_page":50}
    results=[]
    for p in range(1,pages+1):
        params["page"]=p
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if r.status_code!=200:
            break
        d=r.json()
        for item in d.get("items",[]):
            results.append({"repo":item["repository"]["full_name"], "path":item["path"], "url":item["html_url"]})
    return results
