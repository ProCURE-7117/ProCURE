import random
import re
from log import logger
from fileio import FileIO

PROMPT_SYSTEM_ROLE = "system"
PROMPT_USER_ROLE = "user"
PROMPT_AI_ROLE = "assistant"

PROMPT_SYSTEM_CONTENT = "You are an helpful expert in Python language. You are skilled at modifying code while ensuring that its semantics remain unchanged."
PROMPT_MUTATION_1 = "src/mutation1.txt"
PROMPT_MUTATION_2 = "src/mutation2.txt"
PROMPT_MUTATION_3 = "src/mutation3.txt"
PROMPT_MUTATION_4 = "src/mutation4.txt"
PROMPT_MUTATION_5 = "src/mutation5.txt"

def system_prompt():
    prompt = {"role": PROMPT_SYSTEM_ROLE, "content": PROMPT_SYSTEM_CONTENT}
    logger.debug("Successfully read system prompt template to generate system prompt information")
    return prompt

def model_response_prompt(message):
    prompt = {"role": PROMPT_AI_ROLE, "content": message}
    logger.debug("Successfully build ai response for multi-round talk")
    return prompt

def ifelse_flip_prompt(message, analysis):
    part = analysis["If-Else Flip"]
    if len(part) != 0:
        index = random.randint(0,len(part)-1)
        supplement = f"""
The if conditional statement is '{part[index]["if_condition"]}'
Then code in if condition is '{part[index]["then_body"]}'
Then code in else condition is '{part[index]["else_body"]}'
"""
        message = supplement + message

        content = FileIO.file_reader(PROMPT_MUTATION_1).replace("$code$", str(message))
        prompt = {"role": PROMPT_USER_ROLE, "content": content}
        logger.debug("Successfully read mutation prompt template of IF-ELSE-FLIP to build prompt")
        return prompt
    else:
        return None

def independent_swap_prompt(message, analysis):
    part = analysis["Independent Swap"]["pairs"]
    if len(part) != 0:
        group_str = ""
        for index, block in enumerate(part, start=1):
            group_str += str(block) + '\n'
        supplement = f"""
In this code, the independent block includes {len(part)} groups:
{group_str}
You can select one of the groups to modify.
"""
        message = supplement + message
        content = FileIO.file_reader(PROMPT_MUTATION_2).replace("$code$", str(message))
        prompt = {"role": PROMPT_USER_ROLE, "content": content}
        logger.debug("Successfully read mutation prompt template of INDEPENDENT-SWAP to build prompt")
        return prompt
    else:
        return None

def def_use_prompt(message, analysis):
    part = analysis["Def-Use Break"]
    if len(part) != 0:
        index = random.randint(0,len(part)-1)
        first_def = part[index]["first_def"]["code"]
        second_use = "in " + part[index]["uses"][0]["scope"]
        supplement = f"""
In this code, the variable {part[0]["variable_name"]} is defined multiple times:
The first definition statement is: {first_def} 
The second definition statement is {second_use}
You need to rename the variable "{part[0]["variable_name"]}" in the code "{second_use}" and the following parts.
Note that you only change the variable name, not the value.
"""
        message = supplement + message
        content = FileIO.file_reader(PROMPT_MUTATION_3).replace("$code$", str(message))
        prompt = {"role": PROMPT_USER_ROLE, "content": content}
        logger.debug("Successfully read mutation prompt template of DEF-USE to build prompt")
        return prompt
    else:
        return None

def variable_name_random_prompt(message, analysis):
    part = analysis["Variable-Name Invariance"]["variables"]
    if len(part) != 0:
        var_str = ','.join(part)
        supplement = f"""
In this code, The variables you can choose include: {var_str}.
You need to select one or more to change the variable name.
"""
        message = supplement + message
        content = FileIO.file_reader(PROMPT_MUTATION_4).replace("$code$", str(message))
        prompt = {"role": PROMPT_USER_ROLE, "content": content}
        logger.debug("Successfully read mutation prompt template of VARIABLE-NAME-random to build prompt")
        return prompt
    else:
        return None

def variable_name_shuttle_prompt(message, analysis):
    part = analysis["Variable-Name Invariance"]["variables"]
    renaming_map = analysis["Variable-Name Invariance"]["renaming_map"]
    if len(part) != 0:
        var_str = ','.join(analysis["Variable-Name Invariance"]["variables"])
        supplement = f"""
In this code, The variables you can choose include: {var_str}.
Please shuffle variables names according to the following renaming mappiing:
{renaming_map}
"""
        message = supplement + message

        content = FileIO.file_reader(PROMPT_MUTATION_5).replace("$code$", str(message))
        prompt = {"role": PROMPT_USER_ROLE, "content": content}
        logger.debug("Successfully read mutation prompt template of VARIABLE-NAME-shuttle to build prompt")
        return prompt
    else:
        return None

def repair_response_prompt(message):
    content = f"The code you generated has errors:\n {message}.\n Please regenerate complete code according to the mutation requirements to ensure that the syntax of the code is correct and semantically equivalent."
    prompt = {"role": PROMPT_USER_ROLE, "content": content}
    logger.debug("Successfully build REPAIR prompt to repair response")
    return prompt

def extract_code(text):
    pattern = r'```(?:python)\n([\s\S]*?)\n```'
    matches = re.findall(pattern, text, re.MULTILINE)
    
    if matches:
        return matches[0].strip()
    else:
        return ""