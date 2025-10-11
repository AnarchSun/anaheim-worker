import hashlib
import re

def hash_error(obj):
    return hashlib.sha256(obj.encode('utf-8')).hexdigest()

def function_signature_snippet(code):
    m = re.search(r'(def|function|const|export\s+function)\s+([a-zA-Z0-9_]+)\s*\(', code)
    return m.group(2) if m else None
