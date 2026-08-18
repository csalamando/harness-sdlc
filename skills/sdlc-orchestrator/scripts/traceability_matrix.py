#!/usr/bin/env python3
"""traceability_matrix.py — matriz historia -> Gherkin -> test -> código.

Uso: python3 traceability_matrix.py --spec-dir spec/ --tests-dir tests/ --src-dir src/
Detecta historias sin tests y código sin historia (huérfano). Exit 1 si hay brechas.
"""
import os, re, argparse, sys

def collect_ids(root, exts):
    ids = set()
    if os.path.isfile(root):
        text = open(root, encoding="utf-8", errors="ignore").read()
        return {i.upper() for i in re.findall(r"HU-\d+", text, re.IGNORECASE)}
    if not os.path.isdir(root):
        return ids
    for dirpath, _, files in os.walk(root):
        for f in files:
            if any(f.endswith(e) for e in exts):
                try:
                    text = open(os.path.join(dirpath, f), encoding="utf-8", errors="ignore").read()
                except OSError:
                    continue
                ids.update(re.findall(r"HU-\d+", text, re.IGNORECASE))
    return {i.upper() for i in ids}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec-dir", default="spec/")
    ap.add_argument("--tests-dir", default="tests/")
    ap.add_argument("--src-dir", default="src/")
    a = ap.parse_args()
    stories = collect_ids(os.path.join(a.spec_dir, "user-stories.md") if os.path.isfile(os.path.join(a.spec_dir, "user-stories.md")) else a.spec_dir, [".md"])
    tests = collect_ids(a.tests_dir, [".py", ".ts", ".tsx", ".js", ".java", ".cs", ".feature"])
    code  = collect_ids(a.src_dir, [".py", ".ts", ".tsx", ".js", ".java", ".cs"])
    print("| Historia | Gherkin (spec) | Test | Código |")
    print("|---|---|---|---|")
    gaps = 0
    for hu in sorted(stories | tests | code):
        s, t, c = hu in stories, hu in tests, hu in code
        print(f"| {hu} | {'✓' if s else '—'} | {'✓' if t else '✗'} | {'✓' if c else '✗'} |")
        if s and (not t or not c): gaps += 1
        if (t or c) and not s: gaps += 1  # código/test huérfano
    print(f"\nHistorias: {len(stories)} | con test: {len(stories & tests)} | con código: {len(stories & code)}")
    if gaps:
        print(f"BRECHAS: {gaps} filas incompletas (historias sin test/código o código huérfano).")
        sys.exit(1)
    print("Trazabilidad completa.")

if __name__ == "__main__":
    main()
