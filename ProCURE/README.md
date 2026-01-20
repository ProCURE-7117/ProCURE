# ProCURE

ProCURE is a toolkit for automatically generating and augmenting programming datasets using large language models (LLMs). It helps improve LLMs' understanding of programming concepts by creating counterfactual code samples and diverse test cases.

## Main Features
- Automated code mutation and augmentation using LLMs
- Supports popular datasets: HumanEval, MBPP, CodeContests
- Built-in code analysis and verification tools
- Easy integration and customization

## Workflow Overview
1. **Load Data**: Read datasets in formats like parquet or jsonl.
2. **Analyze Code**: Extract code structure and variables for mutation.
3. **Mutate Code**: Use LLMs to generate mutated code samples via various mutators (e.g., if-else flip, variable renaming).
4. **Verify Mutations**: Automatically test mutated code and attempt repairs if needed.
5. **Save Results**: Record all outputs and statistics for further use.

## Quick Start
1. **Install dependencies** (e.g., pandas, pyarrow, openai) and set your LLM API key.
2. **Choose a script** for your dataset:
   - `genhumaneval.py` for HumanEval
   - `genmbpp.py` for MBPP
   - `gencodecontest.py` for CodeContests
3. **Edit script parameters** (input/output paths, etc.) if needed.
4. **Run the script**:
   ```bash
   python genhumaneval.py
   ```
5. **Check the output** files for augmented data and summary statistics.

## Customization
- To add new mutation strategies or change verification logic, edit the relevant scripts or utility modules directly.

---
For more details, see the code and comments in each script.
