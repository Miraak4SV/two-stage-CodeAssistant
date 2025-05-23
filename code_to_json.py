import os
import ast
import json

CODE_DIR = r"d:/Diploma/App/sklearn_Dataset"  # Путь к исходникам
OUTPUT_FILE = "sklearn_knowledge_base.jsonl"

def extract_code_snippets(file_path, rel_path):
    """Извлекает функции и классы из Python-файла через AST."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    snippets = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            start = node.lineno - 1
            end = getattr(node, 'end_lineno', None)

            if end is None:
                continue  # пропускаем, если не можем определить конец (Python < 3.8)

            code_lines = code.splitlines()[start:end]
            code_fragment = "\n".join(code_lines).strip()

            name = node.name
            kind = "Класс" if isinstance(node, ast.ClassDef) else "Функция"

            queries = [
                f"Что делает {kind.lower()} {name}?",
                f"Как работает {kind.lower()} {name}?",
                f"Где используется {name}?"
            ]

            snippets.append({
                "title": f"{kind} {name} в {rel_path}",
                "path": rel_path,
                "content": code_fragment,
                "queries": queries
            })

    return snippets

def build_ast_based_knowledge_base(code_dir, output_file):
    all_snippets = []
    for root, _, files in os.walk(code_dir):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, code_dir)
                snippets = extract_code_snippets(full_path, rel_path)
                all_snippets.extend(snippets)

    with open(output_file, "w", encoding="utf-8") as f:
        for idx, snippet in enumerate(all_snippets):
            snippet["id"] = idx + 1
            f.write(json.dumps(snippet, ensure_ascii=False) + "\n")

    print(f"✅ Сохранено {len(all_snippets)} фрагментов в {output_file}")

if __name__ == "__main__":
    build_ast_based_knowledge_base(CODE_DIR, OUTPUT_FILE)
