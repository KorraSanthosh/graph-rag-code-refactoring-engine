import tree_sitter_python as tspython
from tree_sitter import Language, Parser

class CodeParser:
    """Parses Python code into an AST and extracts entities and calls."""
    def __init__(self):
        self.PY_LANGUAGE = Language(tspython.language())
        self.parser = Parser(self.PY_LANGUAGE)

    def parse_code(self, source_code: str) -> dict:
        tree = self.parser.parse(bytes(source_code, "utf8"))
        root_node = tree.root_node

        extracted_data = {
            "imports": [],
            "classes": [],
            "functions": [],
            "calls": [] # (caller, callee)
        }

        self._traverse_tree(root_node, source_code, extracted_data, current_scope="global")
        return extracted_data

    def _traverse_tree(self, node, source_code, data, current_scope):
        new_scope = current_scope
        
        if node.type in ['import_statement', 'import_from_statement']:
            import_text = source_code[node.start_byte:node.end_byte]
            data["imports"].append(import_text)

        elif node.type == 'class_definition':
            name_node = node.child_by_field_name('name')
            if name_node:
                class_name = source_code[name_node.start_byte:name_node.end_byte]
                data["classes"].append(class_name)
                new_scope = class_name

        elif node.type == 'function_definition':
            name_node = node.child_by_field_name('name')
            if name_node:
                function_name = source_code[name_node.start_byte:name_node.end_byte]
                data["functions"].append(function_name)
                new_scope = function_name

        elif node.type == 'call':
            function_node = node.child_by_field_name('function')
            if function_node:
                callee_name = source_code[function_node.start_byte:function_node.end_byte]
                if function_node.type == 'attribute':
                    attr_name_node = function_node.child_by_field_name('attribute')
                    if attr_name_node:
                         callee_name = source_code[attr_name_node.start_byte:attr_name_node.end_byte]
                
                data["calls"].append((current_scope, callee_name))

        for child in node.children:
            self._traverse_tree(child, source_code, data, new_scope)

if __name__ == "__main__":
    code = """
class MathEngine:
    def add(self, a, b):
        return a + b

def calculate():
    engine = MathEngine()
    return engine.add(1, 2)
"""
    p = CodeParser()
    print(p.parse_code(code))
