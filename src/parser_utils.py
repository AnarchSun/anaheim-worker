import re, json

def parse_tsc(output):
    pattern = re.compile(r'^(.*\\.ts[x]?):(\\d+):(\\d+) - (error|warning) (TS\\d+): (.*)$', re.M)
    errors=[]
    for m in pattern.finditer(output):
        errors.append({"file":m.group(1),"line":int(m.group(2)),"col":int(m.group(3)),"level":m.group(4),"code":m.group(5),"msg":m.group(6)})
    return errors

def parse_eslint_json(output):
    try:
        arr=json.loads(output)
        errors=[]
        for f in arr:
            for m in f.get("messages",[]):
                errors.append({"file":f["filePath"],"line":m.get("line"),"msg":m.get("message"),"rule":m.get("ruleId")})
        return errors
    except Exception:
        return []

def parse_cargo(output):
    pattern = re.compile(r'--> (.*):(\\d+):(\\d+)')
    errors=[]
    for m in pattern.finditer(output):
        errors.append({"file":m.group(1),"line":int(m.group(2))})
    return errors
