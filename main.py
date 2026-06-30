from parser import CodeParser
from graph import DependencyGraph
from llm import LLMEngine
from verifier import SandboxVerifier
import sys

def main():
    # 1. Load Sample Code
    target_file = "sample_target.py"
    try:
        with open(target_file, "r") as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"Error: {target_file} not found.")
        return

    print(f"--- PHASE 1: Parsing {target_file} ---")
    parser = CodeParser()
    metadata = parser.parse_code(source_code)
    print(f"Extracted: {len(metadata['functions'])} functions, {len(metadata['classes'])} classes.")

    print("\n--- PHASE 2 & 3: Building Dependency Graph ---")
    dg = DependencyGraph()
    dg.build_from_metadata(metadata)
    
    # Let's say we want to refactor the 'process_data' function specifically
    target_node = "process_data"
    related = dg.get_related_nodes(target_node)
    context = f"Node '{target_node}' depends on or is called by: {', '.join(related)}"
    print(f"Graph Context for '{target_node}': {context}")

    print("\n--- PHASE 4, 5, 6: LLM Refactoring & Verification Loop ---")
    llm = LLMEngine()
    verifier = SandboxVerifier()

    attempts = 0
    max_attempts = 3
    current_code = source_code
    error_log = None

    while attempts < max_attempts:
        attempts += 1
        print(f"Refactoring Attempt {attempts}...")
        
        refactored = llm.get_refactored_code(current_code, context, error_log)
        if refactored.startswith("Error calling LLM:"):
            print(refactored)
            break
        
        print("Verifying code...")
        success, logs = verifier.verify_code(refactored)
        
        if success:
            print("Success! Refactored code passed verification.")
            print("\nFinal Refactored Code:\n")
            print(refactored)
            # Save the result
            with open("refactored_result.py", "w") as f:
                f.write(refactored)
            break
        else:
            print(f"Verification Failed. Error: {logs[:100]}...")
            error_log = logs
            current_code = refactored # Try again with the broken code and error log

    if attempts == max_attempts and not success:
        print("Reached max attempts without successful verification.")

if __name__ == "__main__":
    main()
