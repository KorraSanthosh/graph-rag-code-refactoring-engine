import logging
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

logger = logging.getLogger(__name__)


class CodeParser:
    """
    Parses Python source code into an AST using Tree-sitter.
    Extracts functions, classes, imports, and call edges with
    proper scope resolution (ClassName.method_name).
    """

    def __init__(self):
        self.PY_LANGUAGE = Language(tspython.language())
        self.parser = Parser(self.PY_LANGUAGE)

    def parse_code(self, source_code: str) -> dict:
        """
        Returns a metadata dict:
        {
            "imports": [str],
            "classes": [str],
            "functions": [str],   # scoped: "ClassName.method" or "function"
            "calls": [(caller, callee)]
        }
        """
        tree = self.parser.parse(bytes(source_code, "utf8"))
        root_node = tree.root_node

        extracted_data: dict = {
            "imports": [],
            "classes": [],
            "functions": [],
            "calls": [],
        }

        self._traverse_tree(
            root_node, source_code, extracted_data, current_scope="global", class_scope=None
        )
        logger.info(
            f"Parsed {len(extracted_data['functions'])} functions, "
            f"{len(extracted_data['classes'])} classes, "
            f"{len(extracted_data['calls'])} call edges."
        )
        return extracted_data

    def _traverse_tree(self, node, source_code: str, data: dict, current_scope: str, class_scope: str | None):
        new_scope = current_scope
        new_class_scope = class_scope

        if node.type in ["import_statement", "import_from_statement"]:
            import_text = source_code[node.start_byte:node.end_byte]
            data["imports"].append(import_text)

        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                class_name = source_code[name_node.start_byte:name_node.end_byte]
                data["classes"].append(class_name)
                new_class_scope = class_name
                new_scope = class_name

        elif node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                func_name = source_code[name_node.start_byte:name_node.end_byte]
                # Scoped node ID: ClassName.method_name or just function_name
                node_id = f"{class_scope}.{func_name}" if class_scope else func_name
                if node_id not in data["functions"]:
                    data["functions"].append(node_id)
                new_scope = node_id

        elif node.type == "call":
            function_node = node.child_by_field_name("function")
            if function_node:
                callee_name = source_code[function_node.start_byte:function_node.end_byte]
                if function_node.type == "attribute":
                    attr_name_node = function_node.child_by_field_name("attribute")
                    if attr_name_node:
                        callee_name = source_code[attr_name_node.start_byte:attr_name_node.end_byte]
                if current_scope != "global":
                    data["calls"].append((current_scope, callee_name))

        for child in node.children:
            self._traverse_tree(child, source_code, data, new_scope, new_class_scope)


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
    result = p.parse_code(code)
    print(result)
