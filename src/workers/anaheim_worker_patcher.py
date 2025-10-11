# anaheim_worker_patcher.py

import json
import re
from pathlib import Path
from anaheim_worker import log, TS_ERRORS_FILE

# -----------------------
# Patch application
# -----------------------
def apply_patch(patch: dict):
    """
    Patch dict format expected:
    {
        "file": "src/module/foo.ts",
        "type": "insert_import" | "create_function" | "add_param" | "change_type",
        "symbol": "Bar",
        "function": "myFn",      # optional for add_param
        "param": "argName",      # optional for add_param
        "paramType": "string"    # optional for add_param
    }
    """
    file_path = Path(patch["file"])
    if not file_path.exists():
        log(f"❌ File not found for patch: {file_path}")
        return False

    code = file_path.read_text(encoding="utf-8")
    patch_type = patch.get("type")

    if patch_type == "insert_import":
        symbol = patch["symbol"]
        if re.search(rf"import\s+.*\b{symbol}\b", code):
            log(f"ℹ️ Import {symbol} already exists in {file_path}")
            return False
        new_import = f"import {{ {symbol} }} from './{file_path.stem}';\n"
        code = new_import + code
        file_path.write_text(code, encoding="utf-8")
        log(f"✅ Import {symbol} inserted in {file_path}")
        return True

    elif patch_type == "create_function":
        symbol = patch["symbol"]
        if re.search(rf"(function|export function)\s+{symbol}\s*\(", code):
            log(f"ℹ️ Function {symbol} already exists in {file_path}")
            return False
        skeleton = f"\nexport function {symbol}(...args: any[]) {{\n  throw new Error('Not implemented');\n}}\n"
        file_path.write_text(code + skeleton, encoding="utf-8")
        log(f"🛠 Function skeleton {symbol} created in {file_path}")
        return True

    elif patch_type == "add_param":
        fn_name = patch["function"]
        param_name = patch["param"]
        param_type = patch.get("paramType", "any")
        pattern = rf"(function\s+{fn_name}\s*\([^)]*)\)"
        match = re.search(pattern, code)
        if not match:
            log(f"❌ Function {fn_name} not found in {file_path}")
            return False
        before = match.group(1)
        updated = before + f", {param_name}: {param_type})"
        code = code[:match.start()] + updated + code[match.end():]
        file_path.write_text(code, encoding="utf-8")
        log(f"➕ Param {param_name}: {param_type} added to {fn_name} in {file_path}")
        return True

    elif patch_type == "change_type":
        symbol = patch["symbol"]
        new_type = patch.get("newType", "any")
        pattern = rf"(\b{symbol}\s*:\s*)[A-Za-z0-9_\[\]\|]+"
        code, n = re.subn(pattern, rf"\1{new_type}", code)
        if n == 0:
            log(f"❌ Type for {symbol} not found in {file_path}")
            return False
        file_path.write_text(code, encoding="utf-8")
        log(f"🔧 Type of {symbol} changed to {new_type} in {file_path}")
        return True

    else:
        log(f"ℹ️ Unknown patch type: {patch_type}")
        return False

# -----------------------
# Apply all patches from JSON
# -----------------------
def apply_ts_actions(actions: list):
    for patch in actions:
        apply_patch(patch)

# -----------------------
# Example usage
# -----------------------
if __name__ == "__main__":
    if TS_ERRORS_FILE.exists():
        try:
            actions = json.loads(TS_ERRORS_FILE.read_text(encoding="utf-8"))
            apply_ts_actions(actions)
            TS_ERRORS_FILE.write_text("[]", encoding="utf-8")  # clear after apply
            log(f"✅ All patches applied and TS_ERRORS_FILE cleared")
        except Exception as e:
            log(f"💥 Failed applying patches: {repr(e)}")
