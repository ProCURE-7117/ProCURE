from log import logger

def verify(function_str, assertions):
    local_scope = {}
    try:
        exec(function_str, local_scope)
    except Exception as e:
        return False, f"Function definition failed: {str(e)}"
    for assertion in assertions:
        try:
            exec(assertion, local_scope)
        except AssertionError:
            return False, f"Assertion failed: {assertion}"
        except Exception as e:
            return False, f"Error during assertion execution: {str(e)}"

    return True, "OK"


def verify_humaneval(function_str, assertion_check_str, function_name):
    local_scope = {}    
    try:
        exec(function_str, local_scope)
    except Exception as e:
        return False, f"Function definition failed: {str(e)}"    
    function = local_scope.get(function_name)
    if function is None:
        return False, f"Function '{function_name}' is not defined."
    try:
        exec(assertion_check_str, local_scope)
        
        check = local_scope.get("check")
        if check is None:
            return False, "No check function found in the assertions."
        check(function)
    except AssertionError as e:
        return False, f"Assertion failed: {str(e)}"
    except Exception as e:
        return False, f"Error during assertion execution: {str(e)}"
    
    return True, "OK"

import sys
import io
import multiprocessing
import contextlib

def execute_function_in_sandbox(function_str, input_str, result_queue):
    """ Execute code in an isolated process, capturing exceptions and output """
    try:
        local_scope = {}

        # Redirect input
        sys.stdin = io.StringIO(input_str)

        # Capture output
        output_capture = io.StringIO()
        with contextlib.redirect_stdout(output_capture), contextlib.redirect_stderr(output_capture):
            exec(function_str, local_scope)

        # Get execution result
        result_str = output_capture.getvalue().strip()
        result_queue.put(("success", result_str))
    except Exception as e:
        result_queue.put(("error", str(e)))

def verify_codecontests(function_str, assertions, timeout=3):
    """ Verify if the code output matches the expected output """
    for i, input_str in enumerate(assertions["input"]):
        expected_output = assertions["output"][i].strip()
        function_str = function_str.replace(".replace(',', '\n'))", ".replace(',', '\\n'))")

        # Use a queue to get the result from the subprocess
        result_queue = multiprocessing.Queue()

        # Create subprocess to execute code
        process = multiprocessing.Process(target=execute_function_in_sandbox, args=(function_str, input_str, result_queue))
        process.start()
        process.join(timeout)  # Set timeout

        # If still running after timeout, terminate subprocess
        if process.is_alive():
            process.terminate()
            process.join()
            return False, "Execution timed out"

        # Get result from subprocess
        if not result_queue.empty():
            status, result_str = result_queue.get()
            if status == "error":
                return False, f"Function execution error: {result_str}"
        else:
            return False, "Unknown error: No output from execution"

        # Normalize line endings to avoid issues across different systems
        result_str = result_str.replace('\r\n', '\n')
        expected_output = expected_output.replace('\r\n', '\n')

        # Compare results
        if result_str != expected_output:
            return False, f"Assertion failed: input {input_str!r} expected {expected_output!r}, got {result_str!r}"

    return True, "OK"