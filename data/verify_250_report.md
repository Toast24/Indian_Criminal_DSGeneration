# Verification report: 250 cases (step 2c)

Run: `python step2c_verify.py usable 250` (qwen3:8b via Ollama), about 10 hours at roughly 2.5 minutes per case.
Cases: the first 250 usable cases from batches 1–3, each with all 55 kept columns (the base fields plus the offence, evidence, procedure and reasoning fields).

## Output files
- `data/dataset_250_verified.csv`: 250 rows × 80 columns. Holds every extracted value, plus `verify_verified`, `verify_flagged` and `verify_flags` for each case.
- `data/verification_sheet.csv`: 13,747 rows, one per case and column. Each row has the value, status, supporting quote, page and note. Flagged rows also carry the closest matching passage from the judgment.
- `data/verify_250_report.txt`: status counts for each column.

## Headline
- **19.0% of cells are flagged** for a human check. **81%** are either confirmed by a quote or are confirmed absences.
- Per case: a median of 31 verified cells and 10 flagged (range 1–25 flagged).

| Status | Cells | Meaning |
|---|---|---|
| verified | 5,683 | quote found in the judgment and the value agrees with it |
| not_stated / not_stated_confirmed | 5,115 | blank value; keyword search finds nothing that contradicts it |
| quote_not_found | 1,570 | **flag**: the model's quote isn't in the text (usually a paraphrase) |
| unsupported | 521 | **flag**: a value was given without any quote |
| not_stated_check | 436 | **flag**: value is blank but the judgment contains relevant keywords |
| partly_verified | 106 | some of the quotes were found |
| value_mismatch | 66 | **flag**: a quote was found but the number or section doesn't match the value |
| case consistency | 16 cases | **flag**: cross-field contradictions |

## Most-flagged columns
- **Free-text summaries** (expected, since these are paraphrases rather than quotes): neutral_facts 84%, prosecution_argument 48%, defence_argument 45%, precedent_relied_upon 44%, investigation_status 42%, trial_duration 41%.
- **Ages** need review: accused_age 62% and victim_age 61% flagged, mostly unsupported. The model guesses ages it cannot back with a quote.
- **Religion** (accused and victim): 33% are not_stated_check. Religious words appear in the judgment, so check these cells before relying on them for the counterfactuals.
- The most reliable columns are case_title, number_of_accused, victim_gender, the judicial factors, high_court_outcome and accused_occupation (≤6% flagged).

## Consistency flags (16 cases)
- 14 cases list a section number that the judgment never mentions. Most are IPC s.34 or s.27, which the model adds by habit.
- 1 case has a fixed-term sentence with no number of years.
- 1 case has a fixed-term sentence of 30 years.

## Recommended review order
1. The 66 value_mismatch cells and the 16 consistency cases. These are the most likely real errors.
2. Ages and religion (unsupported or not_stated_check). These columns matter for the bias dimensions.
3. quote_not_found on summary fields. Spot-check them using the closest passage in the note column; most are paraphrases.
