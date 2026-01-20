from log import logger
from chat import openai_model
from prompt import *
import json
import re
import pandas as pd
from verify import *
from analysis import *

def countefactual_humaneval(src_path, save_path, summary_path):
    # Read data
    dataset = pd.read_parquet(src_path, engine='pyarrow')

    # Mutation mapping
    mutator_map = {
        1: ifelse_flip_prompt,
        2: independent_swap_prompt,
        3: def_use_prompt,
        4: variable_name_random_prompt,
        5: variable_name_shuttle_prompt
    }

    # Initialize statistics
    mutation_counts = {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0}
    mutation_successes = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0}
    mutation_tries = {'a1': 0, 'b1': 0, 'c1': 0, 'd1': 0, 'e1': 0}
    mutation_costs = {'a2': 0, 'b2': 0, 'c2': 0, 'd2': 0, 'e2': 0}
    failed_data_ids = []  # Record data_id that returns None

    results = []  # Store results
    count = 0

    # Iterate over each task in the dataset
    for raw_data in dataset.itertuples():
        count += 1
        # Remove unnecessary commented code
        
        data = raw_data._asdict()
        data_id = data["task_id"]
        data_prompt = data["prompt"]
        data_solution = data["canonical_solution"]
        data_test = data["test"]
        data_entry = data["entry_point"]

        data_code = data_merge(data_prompt, data_solution)
        data_assert = data_test

        mutation_data = {"task_id": data_id, "origin_code": data_code}

        # print(data_code)
        analysis_result = analyze_python_function(data_code)
        if "Analysis failed" in analysis_result:
            continue
    
        if analysis_result is None:
            logger.info(f"Finished processing task {data_id} due to error")
            continue
        data_analysis = json.loads(analysis_result)

        task_mutation_results = []

        # Process each mutator
        for mutator, mutator_func in mutator_map.items():
            # Initialize variables
            prompt = [system_prompt()]
            reponse_code = ""
            check = False
            mutation_key = f"{mutator_func.__name__.lower()}".replace("_prompt", "_code")
            mutation_result = {"signal": 0, "code": ""}

            # First attempt to call GPT to generate mutated code
            mutator_prompt = mutator_func(data_code, data_analysis)
            if mutator_prompt is not None:
                mutation_counts[chr(96 + mutator)] += 1  # Count the number of mutations that can be performed
                prompt.append(mutator_prompt)
                response, usage = openai_model(prompt)

                # If response is None, record data_id
                if response is None:
                    failed_data_ids.append(data_id)
                else:
                    reponse_code = extract_code(response)
                    check, msg = verify_humaneval(reponse_code, data_assert, data_entry)

                    # Record the number of attempts and cost
                    mutation_tries[chr(96 + mutator) + '1'] += 1
                    mutation_costs[chr(96 + mutator) + '2'] += usage

                    # If the first attempt fails, try to repair up to 3 times
                    if not check:
                        for _ in range(4):
                            prompt.append(model_response_prompt(reponse_code))
                            prompt.append(repair_response_prompt(msg))

                            response, usage = openai_model(prompt)
                            # Check again if response is None
                            if response is None:
                                failed_data_ids.append(data_id)
                                break

                            reponse_code = extract_code(response)
                            check, msg = verify_humaneval(reponse_code, data_assert, data_entry)

                            mutation_tries[chr(96 + mutator) + '1'] += 1
                            mutation_costs[chr(96 + mutator) + '2'] += usage

                            if check:
                                break
                            else:
                                # Remove the last two repair prompts
                                prompt = prompt[:-2]

            # If mutation is not possible, record the original code
            if mutator_prompt is None:
                mutation_result["signal"] = 0
                mutation_result["code"] = ""
                logger.info(f"Task {data_id} hasn't condition for mutator {mutator}")
            else:
                if check:
                    mutation_result["signal"] = 1
                    mutation_result["code"] = reponse_code
                    mutation_successes[chr(64 + mutator)] += 1  # Count the number of successful mutations
                    logger.info(f"Task {data_id} mutation succeeded for mutator {mutator}")
                else:
                    mutation_result["signal"] = 2
                    mutation_result["code"] = ""
                    logger.info(f"Task {data_id} mutation failed for mutator {mutator}")

            # Store each mutation result using mutation_key
            mutation_data[mutation_key] = mutation_result
            task_mutation_results.append(mutation_result)

        # Save the mutation result for the task
        results.append(mutation_data)
        logger.info(f"Finished processing task {data_id}")

    # Write final results
    with open(save_path, 'w') as f:
        for res in results:
            f.write(json.dumps(res) + "\n")

    # Write summary information to a text file
    with open(summary_path, 'w') as f:
        summary = [
            f"Number of datasets {count}",
            f"Mutation counts: a = {mutation_counts['a']}, b = {mutation_counts['b']}, c = {mutation_counts['c']}, d = {mutation_counts['d']}, e = {mutation_counts['e']}",
            f"Mutation successes: A = {mutation_successes['A']}, B = {mutation_successes['B']}, C = {mutation_successes['C']}, D = {mutation_successes['D']}, E = {mutation_successes['E']}",
            f"Mutation attempts: a1 = {mutation_tries['a1']}, b1 = {mutation_tries['b1']}, c1 = {mutation_tries['c1']}, d1 = {mutation_tries['d1']}, e1 = {mutation_tries['e1']}",
            f"Mutation costs: a2 = {mutation_costs['a2']}, b2 = {mutation_costs['b2']}, c2 = {mutation_costs['c2']}, d2 = {mutation_costs['d2']}, e2 = {mutation_costs['e2']}",
            f"Failed tasks (OpenAI returned None): {', '.join(map(str, failed_data_ids))}"
        ]
        f.write("\n".join(summary))
        f.write("\n")

    logger.info("Finished writing all results and summary.")



# Example usage
src = "dataset/humaneval/openai_humaneval/test-00000-of-00001.parquet"
dist = "dataset/humaneval/humaneval_counter1.jsonl"
summary = "dataset/humaneval/counter_summary.txt"
countefactual_humaneval(src, dist, summary)
