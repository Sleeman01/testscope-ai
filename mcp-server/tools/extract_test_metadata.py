import ast


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Attribute):
        parts = []
        cur = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))
    if isinstance(node, ast.Name):
        return node.id
    return ast.dump(node)

def _string_literals(node: ast.AST) -> list[str]:
    out = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str) and child.value.strip():
            out.append(child.value)
    return out

def extract_test_metadata(file_content: str) -> dict:
    tree = ast.parse(file_content)
    tests = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
            continue
        decorators = [_decorator_name(d) for d in node.decorator_list]
        fixtures_used = [
            arg.arg for arg in node.args.args
            if arg.arg not in ("self",) and not arg.arg.startswith("_")
        ]
        assert_count = sum(1 for child in ast.walk(node) if isinstance(child, ast.Assert))
        docstring = ast.get_docstring(node)
        tests.append({
            "name": node.name,
            "framework": "pytest",
            "decorators": decorators,
            "docstring": docstring,
            "fixtures_used": fixtures_used,
            "assert_count": assert_count,
            "string_literals": _string_literals(node),
            "line_range": [node.lineno, node.end_lineno or node.lineno],
        })
    return {"tests": tests}
