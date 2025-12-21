# Policy Matcher

An intelligent Clinical Decision Support system that digitizes medical policies and automates Prior Authorization (PA) evaluations.

## Features
- **Smart Ingestion**: Extracts and classifies policy criteria (Medical Necessity, Exclusions, etc.) from PDFs.
- **Human-in-the-Loop**: CLI-based review workflow to approve or edit extracted rules.
- **Rule Registry**: Versioned storage for policy rules.
- **Vector Search**: Semantic retrieval of rules using OpenSearch.
- **Decision Engine**: Deterministic evaluation of patient data against policy rules.

## Installation

1.  **Prerequisites**:
    -   Python 3.10+
    -   OpenSearch running locally (port 9200)

2.  **Setup**:
    ```bash
    # Install dependencies
    uv pip install -e .
    ```

## Usage

### 1. Ingestion Pipeline
Turn a PDF policy into computable rules.

**Step 1: Ingest & Mine**
Process the PDF and generate "Draft" rules in the registry.
```bash
.venv/bin/python -m policy_matcher.run_pipeline --policy "data/Diabetes Mellitus Testing.pdf"
```

**Step 2: Review Rules**
Review draft rules and approve them.
```bash
.venv/bin/python -m policy_matcher.pipeline.review
# Use --auto-approve for demo purposes
```

**Step 3: Index**
Push approved rules to the search engine.
```bash
.venv/bin/python -m policy_matcher.run_indexing
```

### 2. Run Decision Engine
Evaluate a patient against the ingested rules.

```bash
.venv/bin/python -m policy_matcher.main --patient "data/sample_patient.json"
```

## Project Structure
- `src/policy_matcher/pipeline/`: Ingestion, Mining, Registry, and Indexing logic.
- `src/policy_matcher/rules.py`: Rule definitions and Evaluation Engine.
- `src/policy_matcher/main.py`: Runtime entry point.
- `data/`: Storage for PDFs, Registry JSON, and Sample Data.
