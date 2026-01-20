from log import logger
from chat import openai_model
from prompt import *
import json
from verify import *
from fileio import FileIO
from analysis import *

def countefactual_humaneval(src_path, save_path, summary_path, slice_count):
    # Read datasets
    raw_dataset = FileIO.read_jsonl(src_path)
    slice_start = 1000 * (slice_count - 1)
    slice_stop = len(raw_dataset) if slice_count == 8 else 1000 * slice_count
    dataset = raw_dataset[slice_start:slice_stop]

    # Mutation map to avoid repetitive code
    mutator_map = {
        1: ifelse_flip_prompt,
        2: independent_swap_prompt,
        3: def_use_prompt,
        4: variable_name_random_prompt,
        5: variable_name_shuttle_prompt
    }

    mutation_counts = {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0}
    mutation_successes = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0}
    mutation_tries = {'a1': 0, 'b1': 0, 'c1': 0, 'd1': 0, 'e1': 0}
    mutation_costs = {'a2': 0, 'b2': 0, 'c2': 0, 'd2': 0, 'e2': 0}
    failed_data_names = []

    results = []
    total_processed = 0
    
    # Traverse every piece of data
    for idx, data in enumerate(dataset):
        total_processed += 1
        
        data_name = data["data_name"]
        data_code = data["data_code"]
        data_assert = data["data_assert"]

        mutation_data = {"data_name": data_name, "origin_code": data_code}

        analysis_result = analyze_python_function(data_code)
        if analysis_result is None or "Analysis failed" in analysis_result:
            continue
        data_analysis = json.loads(analysis_result)

        for mutator, mutator_func in mutator_map.items():
            prompt = [system_prompt()]
            reponse_code = ""
            check = False
            mutation_key = f"{mutator_func.__name__.lower()}".replace("_prompt", "_code")
            mutation_result = {"signal": 0, "code": ""}

            mutator_prompt = mutator_func(data_code, data_analysis)
            if mutator_prompt:
                mutation_counts[chr(96 + mutator)] += 1
                prompt.append(mutator_prompt)
                response, usage = openai_model(prompt)

                if response is None:
                    failed_data_names.append(data_name)
                else:
                    reponse_code = extract_code(response)
                    check, msg = verify_codecontests(reponse_code, data_assert)
                    mutation_tries[chr(96 + mutator) + '1'] += 1
                    mutation_costs[chr(96 + mutator) + '2'] += usage

                    if not check:
                        for _ in range(4):
                            prompt.append(model_response_prompt(reponse_code))
                            prompt.append(repair_response_prompt(msg))
                            response, usage = openai_model(prompt)
                            if response is None:
                                failed_data_names.append(data_name)
                                break
                            reponse_code = extract_code(response)
                            check, msg = verify_codecontests(reponse_code, data_assert)
                            mutation_tries[chr(96 + mutator) + '1'] += 1
                            mutation_costs[chr(96 + mutator) + '2'] += usage
                            if check:
                                break
                            else:
                                prompt = prompt[:-2]

            if mutator_prompt is None:
                mutation_result["signal"] = 0
                mutation_result["code"] = ""
            else:
                if check:
                    mutation_result["signal"] = 1
                    mutation_result["code"] = reponse_code
                    mutation_successes[chr(64 + mutator)] += 1
                else:
                    mutation_result["signal"] = 2
                    mutation_result["code"] = ""

            mutation_data[mutation_key] = mutation_result

        results.append(mutation_data)
        logger.info(f"Finished processing task {data_name}")

        if len(results) >= 50:
            with open(save_path, 'a') as f:
                for res in results:
                    f.write(json.dumps(res) + "\n")
            results.clear()

            with open(summary_path, 'a') as f:
                summary = [
                    f"Current progress: {total_processed}",
                    f"Mutation counts: a = {mutation_counts['a']}, b = {mutation_counts['b']}, c = {mutation_counts['c']}, d = {mutation_counts['d']}, e = {mutation_counts['e']}",
                    f"Mutation successes: A = {mutation_successes['A']}, B = {mutation_successes['B']}, C = {mutation_successes['C']}, D = {mutation_successes['D']}, E = {mutation_successes['E']}",
                    f"Mutation attempts: a1 = {mutation_tries['a1']}, b1 = {mutation_tries['b1']}, c1 = {mutation_tries['c1']}, d1 = {mutation_tries['d1']}, e1 = {mutation_tries['e1']}",
                    f"Mutation costs: a2 = {mutation_costs['a2']}, b2 = {mutation_costs['b2']}, c2 = {mutation_costs['c2']}, d2 = {mutation_costs['d2']}, e2 = {mutation_costs['e2']}",
                    f"Failed tasks: {', '.join(map(str, failed_data_names))}"
                ]
                f.write("\n".join(summary))
                f.write("\n\n")

    if results:
        with open(save_path, 'a') as f:
            for res in results:
                f.write(json.dumps(res) + "\n")

    with open(summary_path, 'a') as f:
        summary = [
            f"[Final] Total processed: {total_processed}",
            f"Mutation counts: a = {mutation_counts['a']}, b = {mutation_counts['b']}, c = {mutation_counts['c']}, d = {mutation_counts['d']}, e = {mutation_counts['e']}",
            f"Mutation successes: A = {mutation_successes['A']}, B = {mutation_successes['B']}, C = {mutation_successes['C']}, D = {mutation_successes['D']}, E = {mutation_successes['E']}",
            f"Mutation attempts: a1 = {mutation_tries['a1']}, b1 = {mutation_tries['b1']}, c1 = {mutation_tries['c1']}, d1 = {mutation_tries['d1']}, e1 = {mutation_tries['e1']}",
            f"Mutation costs: a2 = {mutation_costs['a2']}, b2 = {mutation_costs['b2']}, c2 = {mutation_costs['c2']}, d2 = {mutation_costs['d2']}, e2 = {mutation_costs['e2']}",
            f"Failed tasks: {', '.join(map(str, failed_data_names))}"
        ]
        f.write("\n".join(summary))
        f.write("\n")

    logger.info("Finished writing all results and summary.")

# Example usage
slice_count = 8
src = "dataset/codecontests/codecontests.jsonl"
dist = f"dataset/codecontests/codecontests_counter_{slice_count}.jsonl"
summary = f"dataset/codecontests/counter_summary_{slice_count}.txt"
countefactual_humaneval(src, dist, summary, slice_count)