from pathlib import Path
import re
import traceback
from worker_full import log  # utiliser ton log existant du worker

# -----------------------
# Patch TypeScript helpers
# -----------------------
def insert_import(target_file: Path, symbol: str, module: str = ""):
    """
    Ajoute un import en haut du fichier TypeScript si pas déjà présent.
    Exemple: import { symbol } from 'module';
    """
    try:
        content = target_file.read_text(encoding="utf-8")
        import_line = f"import {{ {symbol} }} from '{module}';" if module else f"import {{ {symbol} }};"
        if import_line not in content:
            lines = content.splitlines()
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("import "):
                    insert_idx = i + 1
            lines.insert(insert_idx, import_line)
            target_file.write_text("\n".join(lines), encoding="utf-8")
            log(f"🛠️ Inserted import {symbol} in {target_file}")
    except Exception as e:
        log(f"💥 insert_import failed for {target_file}: {repr(e)}\n{traceback.format_exc()}")

def patch_type_annotation(target_file: Path, symbol: str, new_type: str):
    """
    Change le type d'une variable ou paramètre dans un fichier TypeScript.
    """
    try:
        content = target_file.read_text(encoding="utf-8")
        pattern = re.compile(rf"(\b{symbol}\b\s*:\s*)[a-zA-Z0-9_]+")
        new_content, n = pattern.subn(rf"\1{new_type}", content)
        if n > 0:
            target_file.write_text(new_content, encoding="utf-8")
            log(f"🛠️ Patched type of {symbol} to {new_type} in {target_file}")
    except Exception as e:
        log(f"💥 patch_type_annotation failed for {target_file}: {repr(e)}\n{traceback.format_exc()}")

def create_function(target_file: Path, function_name: str, params: str = "", return_type: str = "void"):
    """
    Crée une fonction TypeScript si elle n'existe pas déjà.
    """
    try:
        content = target_file.read_text(encoding="utf-8")
        if function_name not in content:
            func_def = f"\nexport function {function_name}({params}): {return_type} {{\n    // TODO\n}}\n"
            target_file.write_text(content + func_def, encoding="utf-8")
            log(f"🛠️ Created function {function_name} in {target_file}")
    except Exception as e:
        log(f"💥 create_function failed for {target_file}: {repr(e)}\n{traceback.format_exc()}")

def patch_function_signature(target_file: Path, function_name: str, param_name: str, param_type: str = "any"):
    """
    Ajoute ou modifie un paramètre dans une fonction TypeScript existante.
    """
    try:
        content = target_file.read_text(encoding="utf-8")
        pattern = re.compile(rf"(function\s+{function_name}\s*\()(.*?)(\))", re.DOTALL)
        def repl(match):
            params = match.group(2).strip()
            param_list = [p.strip() for p in params.split(",") if p.strip()]
            updated = False
            for i, p in enumerate(param_list):
                if p.startswith(f"{param_name}:"):
                    param_list[i] = f"{param_name}: {param_type}"
                    updated = True
            if not updated:
                param_list.append(f"{param_name}: {param_type}")
            return f"{match.group(1)}{', '.join(param_list)}{match.group(3)}"
        new_content, n = pattern.subn(repl, content)
        if n > 0:
            target_file.write_text(new_content, encoding="utf-8")
            log(f"🛠️ Patched function signature {function_name} in {target_file}")
    except Exception as e:
        log(f"💥 patch_function_signature failed for {target_file}: {repr(e)}\n{traceback.format_exc()}")
