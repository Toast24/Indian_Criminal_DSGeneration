"""Runs steps 2-5 batch by batch: each batch of 150 judgments is extracted (step 2, then step 2b's extra fields and
step 2c's verification for the usable cases), turned into base cases and counterfactual
prompts, run on the model under test and analysed before the next batch starts.

Usage: python run_batches.py [first_batch] [last_batch] [--prep-only]   (batches numbered from 1; default: all)
--prep-only stops each batch after the counterfactual prompts (steps 2-4), without running the model under test.
Needs data/selected_cases.csv and the PDFs from step 1. Resumable: finished extractions and responses are skipped.
Models: EXTRACT_LLM_* for extraction, TEST_LLM_* for the model under test (both default to LLM_* / local qwen3:8b).
Per batch, data/batches/batch_NN/ gets dataset_base_cases.csv, counterfactual_prompts.csv, responses_<model>.jsonl
and bias_results.csv; data/bias_results_all.csv pools every batch finished so far.
"""
import os
import sys
import time

import pandas as pd

from pipeline_common import DATA
from step2_extract import extract_paths
from step2b_extract_extra import ALL_GROUPS, extract_extra_paths
from step2c_verify import report as verification_report, verify_paths
from step3_build_dataset import build_base
from step4_counterfactuals import build
from step5_run_and_analyse import analyse, responses_path, run

BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '150'))
BATCH_ROOT = os.path.join(DATA, 'batches')


def run_batch(k, paths, prep_only=False):
    label = f'[batch {k}] '
    folder = os.path.join(BATCH_ROOT, f'batch_{k:02d}')
    os.makedirs(folder, exist_ok=True)
    t0 = time.time()

    extract_paths(paths, label=label)
    # Second pass (offence/evidence/procedure/reasoning) only for cases that make it into the dataset
    usable = build_base(paths, verbose=False)['path'].tolist()
    extract_extra_paths(usable, ALL_GROUPS, label=label)
    # Step 2c: supporting quotes, "Not stated" keyword search and consistency checks for every usable case
    verify_paths(usable, label=label)
    base = build_base(paths, verbose=False)
    base.to_csv(os.path.join(folder, 'dataset_base_cases.csv'), index=False)
    prompts = build(base)
    prompts.to_csv(os.path.join(folder, 'counterfactual_prompts.csv'), index=False)
    print(f'{label}{len(base)} usable base cases of {len(paths)} -> {len(prompts)} prompts', flush=True)
    if prompts.empty or prep_only:
        print(f'{label}prepared in {(time.time() - t0) / 60:.0f} min', flush=True)
        return
    run(prompts=prompts, out=responses_path(folder), label=label)
    analyse([responses_path(folder)], os.path.join(folder, 'bias_results.csv'))
    print(f'{label}done in {(time.time() - t0) / 60:.0f} min', flush=True)


def main():
    args = [a for a in sys.argv[1:] if a != '--prep-only']
    prep_only = '--prep-only' in sys.argv
    sel = pd.read_csv(os.path.join(DATA, 'selected_cases.csv'))
    batches = [sel['path'].iloc[i:i + BATCH_SIZE].tolist() for i in range(0, len(sel), BATCH_SIZE)]
    first = int(args[0]) if args else 1
    last = int(args[1]) if len(args) > 1 else len(batches)
    print(f'{len(sel)} judgments in {len(batches)} batches of up to {BATCH_SIZE}; running {first}-{last}', flush=True)
    for k in range(first, last + 1):
        run_batch(k, batches[k - 1], prep_only)
        verification_report()
        if prep_only:
            continue
        finished = [responses_path(os.path.join(BATCH_ROOT, f'batch_{j:02d}')) for j in range(1, k + 1)]
        finished = [f for f in finished if os.path.exists(f)]
        if finished:
            print(f'=== pooled results over {len(finished)} batch(es) ===', flush=True)
            analyse(finished, os.path.join(DATA, 'bias_results_all.csv'))


if __name__ == '__main__':
    main()
