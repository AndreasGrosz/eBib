#!/usr/bin/env python3
"""
Test-Script für die line_matches_query Funktion
"""

from boolean import BooleanAlgebra

algebra = BooleanAlgebra()

FIELD_MAP = {
    "datum": 0,
    "name": 3,
    "ext": 4,
}

FIELD_ALIASES = {
    "dateiname": "name",
    "docdatum": "datum",
}

TAG_DEFS = {
    "#text": {"pdf", "doc", "docx", "txt", "djvu", "odt"},
    "#audio": {"mp3", "wav", "flac", "ogg", "m4a"},
    "#image": {"jpg", "jpeg", "png", "gif", "bmp", "svg", "tiff"},
}

def line_matches_query(line, query_expr):
    print(f"Query: {query_expr}")
    print(f"Line: {line}")
    
    expr = algebra.parse(query_expr)
    print(f"Parsed expression: {expr} (Type: {type(expr)})")
    
    values = set(c.lower() for c in line)

    ext = line[FIELD_MAP["ext"]].lower()
    for tag, extensions in TAG_DEFS.items():
        if ext in extensions:
            values.add(tag.lower())

    print(f"Values set: {values}")

    # Spezialbehandlung für einfache Symbole
    if isinstance(expr, algebra.Symbol):
        lit = expr.obj.lower()
        print(f"Simple symbol: {lit}")
        if ':' in lit:
            field, val = lit.split(':', 1)
            field = FIELD_ALIASES.get(field, field)
            idx = FIELD_MAP.get(field)
            if idx is not None:
                result = val.lower() in line[idx].lower()
                print(f"Field search result: {result}")
                return result
            return False
        else:
            result = lit in values
            print(f"Simple search result: {result}")
            return result

    # Für komplexere Ausdrücke: Rekursive Auswertung
    def evaluate_expr(node):
        print(f"Evaluating node: {node} (Type: {type(node)})")
        
        if isinstance(node, algebra.Symbol):
            lit_raw = node.obj
            lit = lit_raw.lower()
            print(f"Symbol literal: {lit}")

            if ':' in lit:
                field, val = lit.split(':', 1)
                field = FIELD_ALIASES.get(field, field)
                idx = FIELD_MAP.get(field)
                if idx is not None:
                    result = val.lower() in line[idx].lower()
                    print(f"Field {field}:{val} -> {result}")
                    return result
                else:
                    print(f"Unknown field: {field}")
                    return False
            else:
                result = lit in values
                print(f"Value {lit} in values -> {result}")
                return result
        
        elif hasattr(node, 'args'):  # AND, OR, NOT Operationen
            class_name = node.__class__.__name__
            print(f"Operation: {class_name}, Args: {node.args}")
            
            if class_name == 'AND':
                results = [evaluate_expr(arg) for arg in node.args]
                result = all(results)
                print(f"AND {results} -> {result}")
                return result
            elif class_name == 'OR':
                results = [evaluate_expr(arg) for arg in node.args]
                result = any(results)
                print(f"OR {results} -> {result}")
                return result
            elif class_name == 'NOT':
                sub_result = evaluate_expr(node.args[0])
                result = not sub_result
                print(f"NOT {sub_result} -> {result}")
                return result
        
        print(f"Unknown node type, returning False")
        return False

    result = evaluate_expr(expr)
    print(f"Final result: {result}")
    return result

# Test
if __name__ == "__main__":
    # Beispiel-Zeile aus TSV
    test_line = ["2023-01-01", "link", "/path/to", "archive.pdf", "pdf", "1024", "2023-01-01", "md5hash"]
    
    # Tests
    test_queries = [
        "ark",
        "name:ark",
        "name:archive",
        "(name:ark OR name:arc)",
        "ext:pdf",
        "#text"
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        try:
            result = line_matches_query(test_line, query)
            print(f"SUCCESS: '{query}' -> {result}")
        except Exception as e:
            print(f"ERROR: '{query}' -> {e}")
        print('='*50)