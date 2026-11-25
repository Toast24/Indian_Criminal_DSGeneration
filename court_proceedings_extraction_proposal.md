# Proposal: Traceable Extraction of Court Proceedings into Structured Case Data

**Objective.** Build a reliable, human-validated pipeline that converts
digitally generated court PDFs into a user-defined dataset. The system
should support both single-document cases and cases represented by
multiple PDFs, while ensuring every extracted value or paragraph can be
traced to its source.

## Proposed pipeline

``` mermaid
flowchart TD
    A["Court PDFs<br/>(orders, judgments, petitions, affidavits, etc.)"] --> B["1. Ingest & register<br/>Case/document IDs • file hash • metadata"]
    B --> C["2. Extract native PDF text<br/>Page order • paragraphs • headings • tables"]
    C --> D["3. Organise documents<br/>Document type • case association • sections"]
    D --> E["4. Schema-driven extraction<br/>Retrieve relevant passages per field<br/>Extract values, lists or paragraphs"]
    E --> F["5. Evidence & consistency checks<br/>Quote-to-source check • attribution<br/>conflicts • missing/ambiguous fields"]
    F --> G["6. Human review<br/>PDF + highlighted evidence beside fields<br/>Approve • edit • reject • flag"]
    G --> H["7. Publish approved dataset"]
    H --> I["CSV / Excel / JSON / Database"]
    F -. "Evidence and review history" .-> J["Provenance ledger"]
    G -. "Reviewer decisions and edits" .-> J
    H -. "Links each field to evidence" .-> J
```

## How information moves through the system

1.  **Ingest and identify.** Each PDF is stored unchanged and assigned a
    document ID. A case ID groups documents belonging to the same
    matter. File hashes and basic metadata help detect duplicates and
    preserve an audit trail.

2.  **Extract and organise.** Since the PDFs contain digitally embedded
    text, the system reads the native text layer rather than running
    OCR. It preserves page numbers, paragraph/section boundaries,
    headings, tables and text positions where available. Documents are
    classified by type (for example, petition, counter-affidavit, order
    or judgment) and associated with the relevant case. Files with
    broken or unusable text layers are flagged for manual handling.

3.  **Extract against the requested schema.** The user defines the
    output columns and, for each field, its data type and extraction
    rule---for example, an exact date, a party name, a list of statutory
    sections, or a paragraph describing the court's reasoning. The
    system locates relevant passages and extracts each field separately.
    It records "not found", "ambiguous" or "conflicting" rather than
    guessing or filling gaps.

4.  **Attach evidence and check meaning.** Every proposed field is
    paired with the exact supporting passage and its document, page and
    paragraph/section reference. Checks confirm that quoted evidence
    exists in the source and flag inconsistent dates, names or values.
    Where documents disagree, the system retains the competing claims
    and their sources for review rather than silently choosing one.

5.  **Human approval before dataset release.** A reviewer sees the
    proposed field alongside the source PDF at the cited page, with the
    supporting passage highlighted. They can approve, edit, reject, or
    mark the field as missing, ambiguous or conflicting. Only approved
    fields enter the final dataset.

## Essential design safeguards

-   **Preserve legal attribution:** distinguish allegations,
    submissions, witness statements, court observations, judicial
    findings and operative directions. An allegation must never be
    represented as a fact found by the court.
-   **Keep field-level provenance:** store the extracted value, exact
    evidence text, source document ID, page and paragraph/section,
    extraction status, reviewer decision and edit history. If a field
    relies on multiple passages, link all of them.
-   **Separate dataset from audit trail:** deliver a clean
    CSV/Excel/JSON/database view, while maintaining a linked evidence
    ledger so every cell can be checked back to the original PDF.
-   **Do not overwrite source material:** retain original PDFs and their
    hashes; corrections should create a review history, not erase prior
    decisions.

**Expected output:** a structured case dataset whose fields are
human-approved and independently traceable to the precise passages in
the original court documents. The pipeline assists extraction; the
reviewer remains the final authority.
