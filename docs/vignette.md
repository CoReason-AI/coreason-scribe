# The Architecture and Utility of coreason-scribe

### 1. The Philosophy (The Why)

In the highly regulated world of GxP (Good Automated Manufacturing Practice), documentation is often a trailing indicator of reality. The "Validation Gap" occurs when the code—the source of truth—evolves, but the accompanying System Design Specifications (SDS) and Requirements Traceability Matrices (RTM) remain static. This drift is not just a bureaucratic nuisance; it is a patient safety risk.

**coreason-scribe** was built to close this gap by treating **Documentation as Code**. Its core philosophy is simple: **"Code is Truth. AI Drafts. Humans Ratify. Diffs Reveal Risk."**

Instead of asking developers to manually update Word documents, `coreason-scribe` acts as an automated "Compliance Officer in a Box." It parses the codebase to generate draft specifications, enforcing a rigorous **"Draft-Review-Sign"** workflow. It ensures that no release is published without a cryptographically signed artifact that proves the software creates the intended outcome. By surfacing "Logical Drift"—the subtle divergence between what the code does and what the requirements say it does—it allows humans to focus on high-value verification rather than administrative formatting.

### 2. Under the Hood (The Dependencies & Logic)

The architecture of `coreason-scribe` is designed for auditability and precision, leveraging a specific stack to meet regulatory rigor:

*   **`pydantic`**: Defines the immutable schema for `Requirement`, `DraftSection`, and `SignatureBlock`. This ensures that every artifact adheres to a strict structure, preventing malformed data from entering the compliance record.
*   **`weasyprint`**: Unlike standard HTML-to-PDF converters, `weasyprint` supports CSS Paged Media standards. This allows `coreason-scribe` to generate formal, paginated regulatory documents with proper headers, footers, and watermarks, suitable for FDA submission.
*   **`gitpython`**: Grounds every draft in the specific Git commit hash of the source code, ensuring absolute traceability between the documentation version and the exact state of the software.
*   **`jinja2`**: Separates the presentation layer (regulatory templates) from the content generation, allowing the format to evolve independently of the analysis logic.

**The Semantic Logic**
At the heart of the tool is the **`SemanticInspector`**. Instead of treating code as text, it parses the Python **Abstract Syntax Tree (AST)**. It extracts functions and classes, computes SHA-256 hashes of their source segments, and generates a "Draft Artifact."

This enables the **`SemanticDeltaEngine`**. When a new version is built, the engine doesn't just show a line-by-line diff. It compares the semantic hashes. If the code logic changes but the documentation text remains identical, it flags a **Logic Change**, alerting the reviewer that the documentation is likely stale. Conversely, if only the text changes, it records a **Text Change**. This "Semantic Delta" drastically reduces review fatigue by highlighting only what matters.

### 3. In Practice (The How)

`coreason-scribe` integrates directly into the CI/CD pipeline and the developer's workflow. Here is how it functions in practice:

#### A. Generating a Draft from Source
The `SemanticInspector` analyzes the raw source code to produce a structured draft. It captures docstrings and computes the unique hash for every function.

```python
from coreason_scribe.inspector import SemanticInspector

# Initialize the inspector
inspector = SemanticInspector()

source_code = """
def calculate_dose(weight_kg):
    '''Calculates patient dosage based on weight.'''
    return weight_kg * 0.5
"""

# Inspect the code to generate draft sections
sections = inspector.inspect_source(source_code, module_name="dose_calc")

for section in sections:
    print(f"ID: {section.id}")
    print(f"Hash: {section.linked_code_hash}")
    print(f"Author: {section.author}") # 'HUMAN' if docstring exists
```

#### B. Detecting Semantic Drift
The `SemanticDeltaEngine` compares the current build against the last signed release. This is crucial for identifying when implementation details have drifted from the approved design.

```python
from coreason_scribe.delta import SemanticDeltaEngine
from coreason_scribe.models import DiffType

# Compare the current draft artifact against the previous signed version
delta_engine = SemanticDeltaEngine()
report = delta_engine.compute_delta(current_artifact, previous_artifact)

for change in report.changes:
    if change.diff_type == DiffType.LOGIC_CHANGE:
        print(f"CRITICAL: Logic changed in {change.section_id} but documentation text is untouched.")
    elif change.diff_type == DiffType.NEW:
        print(f"New functionality detected: {change.section_id}")
```

#### C. Enforcing the Compliance Gate
The `ComplianceEngine` acts as a gatekeeper. It links requirements to test results (`AssayReport`) and enforces coverage rules based on risk. High-risk features (e.g., Patient Safety) must have 100% coverage, or the release is blocked.

```python
from coreason_scribe.matrix import ComplianceEngine, ComplianceStatus

engine = ComplianceEngine()
# Evaluate requirements against the test results
statuses = engine.evaluate_compliance(requirements, assay_report)

# Block release if critical gaps exist
critical_failures = [
    req_id for req_id, status in statuses.items()
    if status == ComplianceStatus.CRITICAL_GAP
]

if critical_failures:
    raise SystemExit(f"Release Blocked: High Risk requirements {critical_failures} are untested.")
else:
    print("Compliance Gate Passed. Ready for Signing.")
```
