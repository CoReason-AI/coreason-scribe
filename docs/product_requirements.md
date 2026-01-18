# Product Requirements Document: coreason-scribe

**Domain:** Automated Compliance, AI-Drafting, Traceability, & Electronic Signatures
**Architectural Role:** The "Compliance Officer in a Box", Unified GxP Documentation Engine
**Core Philosophy:** "Code is Truth. AI Drafts. Humans Ratify. Diffs Reveal Risk."
**Dependencies:** coreason-validator (Schemas), coreason-arbitrage (Drafting), coreason-assay (Test Evidence), coreason-identity (Signatures), coreason-veritas (Audit)

---

## 1. Executive Summary

coreason-scribe is the GxP documentation automation engine for the CoReason ecosystem. It solves the "Validation Gap" where documentation inevitably drifts from code.

It treats **Documentation as Code**. It parses the agent's logic, uses AI to generate human-readable summaries (System Design Specifications), enforces Risk-Based Traceability (Requirements ↔ Tests), and facilitates a rigorous **"Draft-Review-Sign"** workflow. It ensures that no release is published without a cryptographically signed artifact proving it meets all requirements.

## 2. Functional Philosophy

The agent must implement the **Draft-Reason-Diff-Sign Loop**:

1.  **AI as the Drafter (Semantic Inspection):** The system scans the Python AST (Abstract Syntax Tree) and uses coreason-arbitrage to generate a plain-English summary of the business logic. This creates the *Draft* SDS.
2.  **Risk-Based Traceability:** Coverage rules are dynamic. "High Risk" features (Patient Safety) require 100% test coverage and dual review. "Low Risk" features (UI) require basic coverage.
3.  **Semantic Delta (The "Logic Diff"):** We do not show noisy line-by-line code diffs. We surface **Logical Drift**.
    *   *Example:* "Function calc_dose() changed logic, but the linked Requirement REQ-001 text remained the same. Potential mismatch."
4.  **21 CFR Part 11 Signatures:** Documentation is invalid until a human with the specific RBAC role re-authenticates and digitally signs the artifact.

---

## 3. Core Functional Requirements (Component Level)

### 3.1 The Semantic Inspector (The AI Drafter)

**Concept:** A static analysis engine augmented by LLM reasoning.

*   **Mechanism:**
    *   **AST Parsing:** Extracts class structures, function signatures, and dependency graphs from the source code.
    *   **Cognitive Summarization:** Sends code snippets to coreason-arbitrage (Tier 2 Model) with the prompt: *"Summarize this function's business logic and side effects for a compliance auditor."*
*   **Output:** A DraftArtifact where every section is tagged author="AI_GENERATED" and status="UNVERIFIED".

### 3.2 The Risk-Aware Matrix Builder (The Tracer)

**Concept:** Links Requirements to Evidence based on criticality.

*   **Input:** agent.yaml (Requirements + Risk Level) and assay_report.json (Test Results).
*   **Logic:**
    *   **Trace:** Maps REQ-ID ↔ Code Function ↔ TEST-ID.
    *   **Gap Analysis:**
        *   *High Risk:* If Test Coverage < 100%, mark as **CRITICAL GAP**.
        *   *Low Risk:* If Test Coverage < 100%, mark as **WARNING**.
*   **Visualization:** Auto-generates **Mermaid.js** diagrams representing the Agent's Directed Acyclic Graph (DAG), highlighting nodes that have failed validation.

### 3.3 The Semantic Delta Engine (The Diff)

**Concept:** Compares the current Draft against the previous Signed Release.

*   **Logic:**
    *   **Code vs. Spec:** Detects if code changed while the Requirement text remained static (indicating documentation lag).
    *   **Verification Drift:** Detects if a Requirement was "passed" in v1.0 but "failed" or "untested" in v1.1.
*   **Output:** A "Review Packet" highlighting only the sections that have semantically changed, allowing the human reviewer to focus their attention.

### 3.4 The Signing Room (The Notary)

**Concept:** The mechanism for applying legally binding signatures.

*   **State Machine:** Draft → Pending Review → Approved → Signed.
*   **Action:**
    1.  **Freeze:** Hashes the Approved content.
    2.  **Challenge:** Forces the user to re-authenticate (MFA/Password) via coreason-identity to prove presence.
    3.  **Seal:** Appends a Signature Page with the cryptographic hash and user intent ("I approve this design").
    4.  **Watermark:** Removes the "DRAFT" watermark from the final PDF.

---

## 4. Integration Requirements

*   **coreason-foundry (The UI):**
    *   Must provide the **Review Workbench**: A split-screen UI showing "Previous Version" vs. "New Draft" with AI-suggested changes highlighted.
    *   Allows humans to *edit* the AI's draft. (Audit log: "User X replaced AI text").
*   **coreason-publisher (The Gate):**
    *   The Release Pipeline is blocked until scribe.get_status(version) returns SIGNED.
*   **coreason-veritas (The Log):**
    *   Logs the exact timestamp and User ID of the signature event. This is the primary artifact for an FDA audit.

---

## 5. User Stories (Behavioral Expectations)

### Story A: The "Shift-Left" Gate (CI/CD)

**Context:** Developer commits a change to dose_calculator.py (High Risk) but forgets to update the test.
**Action:** CI runs scribe check.
**Result:** Build Fails. Output: "Traceability Error: High Risk Requirement REQ-050 has implementation changes but 0% test coverage."
**Value:** Prevents non-compliant code from even entering the review branch.

### Story B: The "AI Hallucination Check" (Human Review)

**Context:** coreason-arbitrage summarizes a function as "Deletes user data." The code actually just "Archives" it.
**Action:** QA Reviewer sees this in the Review Workbench.
**Edit:** Reviewer modifies the text to "Archives user data."
**Audit:** Scribe records the edit.
**Sign:** Reviewer signs the corrected document.

### Story C: The "Release Certification" (21 CFR Part 11)

**Context:** Release v2.0 is ready.
**Action:** Head of Quality logs into Foundry. Reviews the "Semantic Delta" (only 3 changed files).
**Sign:** Clicks "Approve & Sign." Enters MFA code.
**Result:** Scribe generates Release_v2.0_Certificate.pdf. The file is hashed and stored in Vault. The release is unblocked.

---

## 6. Data Schema

### DocumentationManifest

```python
class RiskLevel(str, Enum):
    HIGH = "HIGH"   # Patient Safety / GxP
    MED = "MED"     # Business Logic
    LOW = "LOW"     # UI / Formatting

class Requirement(BaseModel):
    id: str         # "REQ-001"
    description: str
    risk: RiskLevel
    source_sop: Optional[str] # "SOP-999"
```

### DraftSection (The Review Unit)

```python
class DraftSection(BaseModel):
    id: str                 # "logic_summary_safety"
    content: str            # "The safety module checks..."
    author: Literal["AI", "HUMAN"]
    is_modified: bool       # Logic Diff vs Previous Version
    linked_code_hash: str   # SHA256 of the python source
```

### SignatureBlock

```python
class SignatureBlock(BaseModel):
    document_hash: str      # SHA-256 of the PDF content
    signer_id: str          # User UUID
    signer_role: str        # "Quality_Manager"
    timestamp: datetime
    meaning: str            # "I certify this design specification."
    signature_token: str    # Cryptographic proof from Identity
```

---

## 7. Implementation Directives for the Coding Agent

1.  **PDF Engine:** Use **weasyprint**. It supports robust CSS Paged Media (headers/footers) which is required for formal regulatory documents.
2.  **Diff Engine:** Use gitpython to detect file changes and Python's ast to detect function-level logic changes. Do not rely on simple string comparison for logic diffs.
3.  **Template Strategy:** Use **Jinja2** for the document structure. Keep the layout (SDS, RTM, Test Report) separate from the content generation.
4.  **Fail-Safe:** If coreason-arbitrage (AI) fails to generate a summary, fallback to the code's Docstring. If the Docstring is missing, insert a placeholder [MISSING DOCUMENTATION] and flag as a Validation Warning.
