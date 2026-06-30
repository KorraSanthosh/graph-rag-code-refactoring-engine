
# Graph-RAG Code Refactoring Engine

A Graph Retrieval-Augmented Generation (Graph-RAG) based code refactoring engine that parses Python source code into an Abstract Syntax Tree (AST), constructs a dependency graph, retrieves graph-aware context, and leverages a Large Language Model (LLM) to generate context-aware code refactoring suggestions. Generated code is automatically verified inside an isolated Docker sandbox before acceptance.

---

## Features

- Parses Python source code using **Tree-Sitter**
- Builds a function-level dependency graph using **NetworkX**
- Retrieves graph-aware contextual information for LLM prompting
- Performs automated code refactoring using **OpenAI GPT-4o**
- Verifies generated code inside an isolated **Docker** container
- Falls back to secure local execution when Docker is unavailable
- Handles API failures gracefully
- Modular and extensible architecture

---

## Tech Stack

- Python 3.11
- Tree-Sitter
- Tree-Sitter Python
- NetworkX
- OpenAI API
- Docker SDK
- Python-dotenv

---

## Project Structure

```text
graph-rag-code-refactoring-engine/
│
├── main.py                 # Main pipeline
├── parser.py               # AST parser
├── graph.py                # Dependency graph builder
├── llm.py                  # OpenAI integration
├── verifier.py             # Docker verification
├── sample_target.py        # Sample input code
├── requirements.txt
├── README.md
└── .env
```

---

## Architecture

Python Source Code
        │
        ▼
Tree-Sitter Parser
        │
        ▼
Abstract Syntax Tree (AST)
        │
        ▼
Dependency Graph (NetworkX)
        │
        ▼
Graph Context Retrieval
        │
        ▼
LLM (GPT-4o)
        │
        ▼
Refactored Code
        │
        ▼
Docker Verification
        │
        ▼
Verified Output

---

## Installation

Clone the repository:


git clone https://github.com/KorraSanthosh/graph-rag-code-refactoring-engine.git
cd graph-rag-code-refactoring-engine

Create a virtual environment:


python -m venv venv

Activate it:

### Linux / macOS

```bash
source venv/bin/activate
```

### Windows

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Configuration

Create a `.env` file in the project root:

```text
OPENAI_API_KEY=your_openai_api_key
```

---

## Usage

Run the pipeline:

```bash
python main.py
```

The pipeline performs the following steps:

1. Parse Python source code.
2. Generate an Abstract Syntax Tree.
3. Construct a dependency graph.
4. Retrieve graph-aware context.
5. Generate refactored code using the LLM.
6. Verify the generated code inside Docker.
7. Repeat if verification fails.

---

## Example Output

```text
--- PHASE 1: Parsing sample_target.py ---
Extracted: 3 functions, 0 classes.

--- PHASE 2 & 3: Building Dependency Graph ---
Graph Context:
helper_one
helper_two

--- PHASE 4, 5, 6: LLM Refactoring & Verification Loop ---
Refactoring Attempt 1...
Verification Successful
```

---

## Key Components

| File | Description |
|------|-------------|
| `main.py` | Coordinates the complete Graph-RAG pipeline |
| `parser.py` | Parses Python code into an AST |
| `graph.py` | Constructs dependency graphs |
| `llm.py` | Generates refactored code using the OpenAI API |
| `verifier.py` | Verifies generated code inside Docker |
| `sample_target.py` | Sample input for testing |

---

## Future Improvements

- Multi-language support
- Incremental graph updates
- Vector database integration
- Semantic code search
- CI/CD pipeline
- Web interface
- Multi-file repository analysis
- Automatic unit test generation

---

## Skills Demonstrated

- Retrieval-Augmented Generation (Graph-RAG)
- Abstract Syntax Tree (AST) Parsing
- Dependency Graph Construction
- Prompt Engineering
- Large Language Models (LLMs)
- Docker Sandbox Execution
- Software Architecture
- Automated Code Refactoring
- Python Development

---

## Author

**Korra Santhosh**

- GitHub: https://github.com/KorraSanthosh
- LinkedIn: https://linkedin.com/in/korra-santhosh-032510323

---

## License

This project is licensed under the MIT License.
