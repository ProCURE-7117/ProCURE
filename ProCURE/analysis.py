from log import logger
import ast
import re
import random
import json
import networkx as nx
from typing import Dict, List, Set, Any

# 预定义的内置函数和类型集合
BUILTINS = {'abs', 'all', 'any', 'bool', 'bytearray', 'callable', 'chr', 'classmethod', 'complex', 'delattr', 
            'dict', 'dir', 'divmod', 'enumerate', 'eval', 'filter', 'float', 'format', 'frozenset', 'getattr', 
            'globals', 'hasattr', 'hash', 'help', 'hex', 'id', 'input', 'int', 'isinstance', 'issubclass', 
            'iter', 'len', 'list', 'locals', 'map', 'max', 'memoryview', 'min', 'next', 'object', 'oct', 'open', 
            'ord', 'pow', 'print', 'property', 'range', 'repr', 'reversed', 'round', 'set', 'setattr', 'slice', 
            'sorted', 'staticmethod', 'str', 'sum', 'super', 'tuple', 'type', 'vars', 'zip'}

KEYWORDS = {'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue', 
            'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import', 
            'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield'}

# 添加更多Python内置类型和常用模块
TYPING_BUILTINS = {'List', 'Dict', 'Set', 'Tuple', 'Optional', 'Union', 'Any', 'Callable', 'Generic'}

class CodePerturbationAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.if_else_statements = []
        self.independent_blocks = []
        self.def_use_chains: Dict[str, List[Dict[str, Any]]] = {}
        self.variable_names: Set[str] = set()
        self.user_defined_variables: Set[str] = set()  # 只记录用户定义的变量
        self.renaming_map: Dict[str, str] = {}
        self.assignments = []  # 存储所有变量赋值
        self.scope_stack = []  # 作用域管理栈
        self.cfg = nx.DiGraph()  # 控制流图
        self.current_scope = "global"  # 记录当前作用域
        self.used_vars: Dict[str, List[Dict[str, Any]]] = {}  # 记录变量的使用位置
        self.variable_definitions: Dict[str, List[Dict[str, Any]]] = {}  # 记录变量定义位置
        
    def is_builtin_or_keyword(self, name: str) -> bool:
        """检查是否为内置函数、关键字或typing模块内容"""
        return name in BUILTINS or name in KEYWORDS or name in TYPING_BUILTINS

    def enter_scope(self, scope_name: str) -> None:
        self.scope_stack.append(scope_name)
        self.current_scope = ".".join(self.scope_stack)

    def exit_scope(self) -> None:
        if self.scope_stack:
            self.scope_stack.pop()
        self.current_scope = ".".join(self.scope_stack) if self.scope_stack else "global"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """处理函数定义，包括参数"""
        self.enter_scope(node.name)
        
        # 记录函数参数为首次定义
        for arg in node.args.args:
            var_name = arg.arg
            if not self.is_builtin_or_keyword(var_name):
                self.user_defined_variables.add(var_name)
                self._record_variable_definition(var_name, f"Parameter '{var_name}'", node.lineno, is_param=True)
        
        # 处理返回注解中的变量（但不加入用户定义变量）
        if node.returns and isinstance(node.returns, ast.Name):
            self.variable_names.add(node.returns.id)
        
        self.generic_visit(node)
        self.exit_scope()

    def visit_For(self, node: ast.For) -> None:
        """处理for循环，包括循环变量"""
        loop_vars = self._extract_variable_names(node.target)
        for var in loop_vars:
            if not self.is_builtin_or_keyword(var):
                self.user_defined_variables.add(var)
                self._record_variable_definition(var, f"Loop variable in for at line {node.lineno}", node.lineno)
        
        self.enter_scope(f"for_{len(self.scope_stack)}")
        self.generic_visit(node)
        self.exit_scope()

    def visit_While(self, node: ast.While) -> None:
        """处理while循环"""
        self.enter_scope(f"while_{len(self.scope_stack)}")
        self.generic_visit(node)
        self.exit_scope()

    def visit_If(self, node: ast.If) -> None:
        """处理if语句"""
        if_scope = f"if_{len(self.scope_stack)}"
        self.enter_scope(if_scope)
        
        # 记录If-Else Flip信息
        if isinstance(node, ast.If) and node.orelse:
            condition = ast.unparse(node.test)
            then_body = [ast.unparse(stmt) for stmt in node.body]
            else_body = [ast.unparse(stmt) for stmt in node.orelse]
            self.if_else_statements.append({
                "mutation_type": "If-Else Flip",
                "if_condition": condition,
                "then_body": then_body,
                "else_body": else_body,
                "transformation_rule": "Negate condition using De Morgan's law, swap then/else blocks."
            })
        
        self.generic_visit(node)
        self.exit_scope()

    def visit_Assign(self, node: ast.Assign) -> None:
        """处理赋值语句（包括元组解包）"""
        targets = [t for t in node.targets if isinstance(t, (ast.Name, ast.Tuple))]
        for target in targets:
            for var in self._extract_variable_names(target):
                if not self.is_builtin_or_keyword(var):
                    self.user_defined_variables.add(var)
                    self._record_variable_definition(var, ast.unparse(node), node.lineno)
                    
                    # 记录赋值信息用于独立语句分析
                    assignment_data = {
                        "code": ast.unparse(node),
                        "variable": var,
                        "dependencies": self.get_dependencies(node.value),
                        "scope": self.current_scope,
                        "in_loop": "for_" in self.current_scope or "while_" in self.current_scope,
                        "line": node.lineno
                    }
                    self.assignments.append(assignment_data)
        
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """记录变量的使用"""
        var_name = node.id
        self.variable_names.add(var_name)
        
        if isinstance(node.ctx, ast.Load):
            # 记录使用位置
            self.used_vars.setdefault(var_name, []).append({
                "scope": self.current_scope,
                "line": node.lineno,
                "usage_type": "use"
            })
            
            # 对于用户定义的变量，检查def-use关系
            if var_name in self.user_defined_variables:
                self._check_def_use_relationship(var_name, node.lineno)
        
        self.generic_visit(node)

    def _extract_variable_names(self, node: ast.AST) -> List[str]:
        """递归提取变量名"""
        if isinstance(node, ast.Name):
            return [node.id]
        elif isinstance(node, ast.Tuple):
            return [name for elt in node.elts for name in self._extract_variable_names(elt)]
        elif isinstance(node, ast.Attribute):
            return self._extract_variable_names(node.value)
        return []

    def _record_variable_definition(self, var_name: str, definition: str, lineno: int, is_param: bool = False) -> None:
        """统一记录变量定义"""
        # 排除内置函数和关键字
        if self.is_builtin_or_keyword(var_name):
            return

        self.variable_names.add(var_name)
        
        # 记录定义位置
        if var_name not in self.variable_definitions:
            self.variable_definitions[var_name] = []
            
        self.variable_definitions[var_name].append({
            "scope": self.current_scope,
            "definition": definition,
            "line": lineno,
            "is_parameter": is_param
        })
        
        # 作用域感知的记录
        if var_name in self.def_use_chains:
            # 查找当前作用域是否已有定义
            existing_scope_def = next(
                (item for item in self.def_use_chains[var_name] 
                 if item["scope"] == self.current_scope),
                None
            )
            
            if existing_scope_def:
                if existing_scope_def["second_def"] is None:
                    existing_scope_def["second_def"] = {
                        "code": definition,
                        "line": lineno
                    }
                # 如果已有second_def，不再重复记录
            else:
                self.def_use_chains[var_name].append({
                    "scope": self.current_scope,
                    "first_def": {
                        "code": definition,
                        "line": lineno
                    },
                    "second_def": None,
                    "uses": []
                })
        else:
            self.def_use_chains[var_name] = [{
                "scope": self.current_scope,
                "first_def": {
                    "code": definition,
                    "line": lineno
                },
                "second_def": None,
                "uses": []
            }]

    def _check_def_use_relationship(self, var_name: str, use_line: int) -> None:
        """检查并记录def-use关系"""
        if var_name in self.def_use_chains:
            for chain in self.def_use_chains[var_name]:
                if chain["scope"] == self.current_scope or self.current_scope.startswith(chain["scope"]):
                    chain["uses"].append({
                        "line": use_line,
                        "scope": self.current_scope
                    })

    def get_dependencies(self, node: ast.AST) -> Set[str]:
        """提取变量依赖关系"""
        dependencies = set()

        if isinstance(node, ast.Name):
            dependencies.add(node.id)

        elif isinstance(node, ast.BinOp):
            dependencies.update(self.get_dependencies(node.left))
            dependencies.update(self.get_dependencies(node.right))

        elif isinstance(node, ast.ListComp):
            for generator in node.generators:
                dependencies.update(self.get_dependencies(generator.iter))

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                dependencies.update(self.get_dependencies(node.func.value))
            elif isinstance(node.func, ast.Name):
                dependencies.add(node.func.id)
            for arg in node.args:
                dependencies.update(self.get_dependencies(arg))

        elif isinstance(node, ast.Attribute):
            dependencies.update(self.get_dependencies(node.value))

        elif isinstance(node, ast.For):
            dependencies.update(self.get_dependencies(node.iter))

        elif isinstance(node, ast.While):
            dependencies.update(self.get_dependencies(node.test))

        return dependencies

    def find_independent_statements(self) -> None:
        """查找可以交换的独立语句对"""
        independent_pairs = []
        for i in range(len(self.assignments)):
            for j in range(i + 1, len(self.assignments)):
                stmt1 = self.assignments[i]
                stmt2 = self.assignments[j]

                if stmt1["scope"] != stmt2["scope"]:
                    continue
                if stmt1["in_loop"] or stmt2["in_loop"]:
                    continue

                var1, deps1 = stmt1["variable"], stmt1["dependencies"]
                var2, deps2 = stmt2["variable"], stmt2["dependencies"]

                if var1 in deps2 or var2 in deps1:
                    continue

                uses1 = self.used_vars.get(var1, [])
                uses2 = self.used_vars.get(var2, [])
                line1, line2 = stmt1["line"], stmt2["line"]
                
                conflict = False
                for use in uses1 + uses2:
                    if (line1 < use["line"] < line2) or (line2 < use["line"] < line1):
                        conflict = True
                        break
                
                if not conflict and stmt1["code"] != stmt2["code"]:
                    independent_pairs.append((stmt1["code"], stmt2["code"]))

        unique_pairs = list(map(list, {frozenset(sorted(pair)) for pair in independent_pairs}))
        self.independent_blocks = unique_pairs

    def analyze_variable_name_invariance(self) -> None:
        """生成变量名重映射方案，只包含用户定义的变量"""
        # 只使用用户定义的变量进行重命名
        user_variables = list(self.user_defined_variables)
        
        if len(user_variables) >= 2:
            while True:
                shuffled = user_variables.copy()
                random.shuffle(shuffled)
                self.renaming_map = dict(zip(user_variables, shuffled))
                
                if any(k != v for k, v in self.renaming_map.items()):
                    break
        else:
            self.renaming_map = {}

    def generate_analysis_result(self) -> str:
        """生成最终JSON结果"""
        self.find_independent_statements()
        self.analyze_variable_name_invariance()

        # 生成Def-Use Break分析
        def_use_breaks = []
        for var, chains in self.def_use_chains.items():
            for chain in chains:
                # 如果有使用记录，则说明存在def-use关系
                if chain["uses"]:
                    def_use_entry = {
                        "variable_name": var,
                        "scope": chain["scope"],
                        "first_def": chain["first_def"],
                        "uses": chain["uses"],
                        "modification": f"Break def-use chain by renaming variable '{var}' after first use"
                    }
                    
                    if chain["second_def"]:
                        def_use_entry["second_def"] = chain["second_def"]
                        def_use_entry["modification"] = f"Rename second occurrence of '{var}' in {chain['scope']} scope"
                    
                    def_use_breaks.append(def_use_entry)

        return json.dumps({
            "If-Else Flip": self.if_else_statements,
            "Independent Swap": {
                "pairs": self.independent_blocks,
                "swap_criteria": "Blocks are independent and reordering does not affect correctness."
            },
            "Def-Use Break": def_use_breaks,
            "Variable-Name Invariance": {
                "variables": sorted(list(self.user_defined_variables)),
                "rename_strategy": "Shuffle variable names among themselves.",
                "renaming_map": self.renaming_map
            }
        }, indent=4)

# 测试代码
def analyze_python_function(source_code):
    """分析给定代码并返回扰动分析结果"""
    try:
        tree = ast.parse(source_code)
        analyzer = CodePerturbationAnalyzer()
        analyzer.visit(tree)
        return analyzer.generate_analysis_result()
    except Exception as e:
        return json.dumps({"error": f"Analysis failed: {str(e)}"}, indent=4)


def data_merge(str1: str, str2: str) -> str:
    # 移除str1中的多行注释/文档字符串，同时保持代码的缩进和换行
    def remove_docstrings(code):
        # 匹配以三个双引号或单引号开始和结束的多行注释/文档字符串
        pattern = r'("""[^"]*?"""|\'\'\'[^\']*?\')'
        # 替换匹配到的内容为空字符串，但保留原始代码的换行和缩进
        return re.sub(pattern, lambda match: '\n' * match.group().count('\n'), code, flags=re.DOTALL)
    
    # 清理str1中的多行文档字符串
    cleaned_str1 = remove_docstrings(str1)
    
    # 过滤掉str1中以#开头的单行注释，但保留原始代码的换行和缩进
    lines = []
    for line in cleaned_str1.split('\n'):
        stripped_line = line.strip()
        if stripped_line.startswith('#'):
            # 如果整行是注释，则跳过该行
            continue
        elif stripped_line == '':
            # 如果当前行是空行，检查前一行是否也是空行，如果不是则添加当前空行
            if not (len(lines) > 0 and lines[-1].strip() == ''):
                lines.append(line)
        else:
            # 保留非注释行，包括其原始的缩进和换行
            lines.append(line)
    
    # 合并清理后的str1和str2
    merged_function = '\n'.join(lines) + '\n' + str2
    
    # 再次清理合并后的函数中的多余空行
    final_lines = []
    for line in merged_function.split('\n'):
        stripped_line = line.strip()
        if stripped_line.startswith('#'):
            # 跳过单行注释
            continue
        elif stripped_line == '':
            # 如果当前行是空行，检查前一行是否也是空行，如果不是则添加当前空行
            if not (len(final_lines) > 0 and final_lines[-1].strip() == ''):
                final_lines.append(line)
        else:
            # 保留非注释行，包括其原始的缩进和换行
            final_lines.append(line)
    
    return '\n'.join(final_lines)

def data_split(input_str, func_name):
    # 使用正则表达式匹配所有的 assert candidate 语句
    pattern = r'assert candidate\(.*?\) == .*'
    asserts = re.findall(pattern, input_str)
    asserts = [assert_stmt.replace('candidate', func_name) for assert_stmt in asserts]
    
    return asserts
