import re

class Node:
    pass

class BinOp(Node):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class Condition(Node):
    def __init__(self, left_expr, op, right_expr=None):
        self.left_expr = left_expr
        self.op = op
        self.right_expr = right_expr

class ExprNode(Node):
    pass

class Field(ExprNode):
    def __init__(self, name):
        self.name = name

class Literal(ExprNode):
    def __init__(self, value):
        self.value = value

class ArithOp(ExprNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class FuncCall(ExprNode):
    def __init__(self, func_name, arg):
        self.func_name = func_name
        self.arg = arg

def tokenize(expr):
    token_specification = [
        ('STRING',   r'"[^"]*"|\'[^\']*\''),
        ('OP2',      r'=~|!=|>=|<='),
        ('OP_WORD',  r'\b(?:not in|is_null|in|exists)\b'),
        ('OP1',      r'>|<|=|~'),
        ('MATH_OP',  r'[+\-*/%]'),
        ('AND',      r'\band\b'),
        ('OR',       r'\bor\b'),
        ('LPAREN',   r'\('),
        ('RPAREN',   r'\)'),
        ('WORD',     r'[^\s()=~><!+\-*/%]+'),
        ('SKIP',     r'[ \t]+'),
        ('MISMATCH', r'.'),
    ]
    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
    
    tokens = []
    # Workaround: `not in`, `is_null` can be handled by OP2, but we need to ensure words don't swallow them.
    # To be safe, we just use the regex.
    for mo in re.finditer(tok_regex, expr, re.IGNORECASE):
        kind = mo.lastgroup
        value = mo.group()
        if kind == 'SKIP':
            continue
        elif kind == 'MISMATCH':
            raise ValueError(f"Unexpected token {value!r}")
        if kind == 'STRING':
            value = value[1:-1] # Remove quotes
            # Keep kind as STRING to distinguish from WORD (fields/numbers)
        elif kind in ('AND', 'OR'):
            value = value.upper()
        tokens.append((kind, value))
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected_kind=None):
        tok = self.peek()
        if tok and (expected_kind is None or tok[0] == expected_kind):
            self.pos += 1
            return tok
        return None

    def parse(self):
        if not self.tokens:
            return None
        node = self.parse_or()
        if self.peek() is not None:
            raise ValueError(f"Unexpected trailing tokens: {self.tokens[self.pos:]}")
        return node

    def parse_or(self):
        node = self.parse_and()
        while self.peek() and self.peek()[0] == 'OR':
            op = self.consume('OR')[1]
            right = self.parse_and()
            node = BinOp(node, op, right)
        return node

    def parse_and(self):
        node = self.parse_primary()
        while self.peek() and self.peek()[0] == 'AND':
            op = self.consume('AND')[1]
            right = self.parse_primary()
            node = BinOp(node, op, right)
        return node

    def parse_primary(self):
        tok = self.peek()
        if not tok:
            raise ValueError("Unexpected end of expression")
            
        if tok[0] == 'LPAREN':
            self.consume('LPAREN')
            # Lookahead to see if it's a value expression or boolean
            saved_pos = self.pos
            try:
                node = self.parse_or()
                if self.consume('RPAREN'):
                    return node
            except ValueError:
                pass
            self.pos = saved_pos
            # Fall back to condition
            
        # Parse left expression
        left_expr = self.parse_math_expr()
        
        op_tok = self.consume('OP1') or self.consume('OP2') or self.consume('OP_WORD')
        if not op_tok:
            raise ValueError(f"Expected operator after expression, got {self.peek()}")
            
        op = op_tok[1].lower()
        if op in ('exists', 'is_null'):
            return Condition(left_expr, op)
            
        # Otherwise, need a right expression
        right_expr = self.parse_math_expr()
        return Condition(left_expr, op, right_expr)

    def parse_math_expr(self):
        node = self.parse_term()
        while self.peek() and self.peek()[0] == 'MATH_OP' and self.peek()[1] in ('+', '-'):
            op = self.consume('MATH_OP')[1]
            right = self.parse_term()
            node = ArithOp(node, op, right)
        return node

    def parse_term(self):
        node = self.parse_factor()
        while self.peek() and self.peek()[0] == 'MATH_OP' and self.peek()[1] in ('*', '/', '%'):
            op = self.consume('MATH_OP')[1]
            right = self.parse_factor()
            node = ArithOp(node, op, right)
        return node

    def parse_factor(self):
        tok = self.peek()
        if not tok:
            raise ValueError("Unexpected end of math expression")
            
        if tok[0] == 'LPAREN':
            self.consume('LPAREN')
            node = self.parse_math_expr()
            if not self.consume('RPAREN'):
                raise ValueError("Expected ')'")
            return node

        if tok[0] == 'STRING':
            val = tok[1]
            self.consume('STRING')
            return Literal(val)

        if tok[0] == 'WORD':
            val = tok[1]
            self.consume('WORD')

            # Check for function call
            if self.peek() and self.peek()[0] == 'LPAREN':
                self.consume('LPAREN')
                arg = self.parse_math_expr()
                if not self.consume('RPAREN'):
                    raise ValueError("Expected ')' for function call")
                return FuncCall(val.lower(), arg)

            # It could be a number or a field.
            try:
                num = float(val)
                return Literal(num)
            except ValueError:
                pass
            return Field(val)

        raise ValueError(f"Unexpected token in math expression: {tok}")


def parse_where(expr):
    tokens = tokenize(expr)
    return Parser(tokens).parse()

def eval_expr(node, d: dict):
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, Field):
        if node.name in d:
            return d[node.name]
        # It might be a string literal that wasn't properly typed (e.g. if we didn't differentiate in parser)
        # We will assume if it's not in dict, maybe it's just a string literal.
        return node.name
    if isinstance(node, ArithOp):
        left = eval_expr(node.left, d)
        right = eval_expr(node.right, d)
        try:
            left_num = float(left) if left is not None else 0.0
            right_num = float(right) if right is not None else 0.0
            if node.op == '+': return left_num + right_num
            if node.op == '-': return left_num - right_num
            if node.op == '*': return left_num * right_num
            if node.op == '/': return left_num / right_num if right_num != 0 else None
            if node.op == '%': return left_num % right_num if right_num != 0 else None
        except (ValueError, TypeError):
            # If string concatenation
            if node.op == '+':
                return str(left if left is not None else '') + str(right if right is not None else '')
            return None
    if isinstance(node, FuncCall):
        arg = eval_expr(node.arg, d)
        arg_str = str(arg) if arg is not None else ''
        if node.func_name == 'length':
            return len(arg_str)
        if node.func_name == 'lower':
            return arg_str.lower()
        if node.func_name == 'upper':
            return arg_str.upper()
        if node.func_name == 'trim':
            return arg_str.strip()
        return None
    return None

def evaluate(node, d: dict) -> bool:
    if node is None:
        return True
    if isinstance(node, BinOp):
        if node.op == 'AND':
            return evaluate(node.left, d) and evaluate(node.right, d)
        elif node.op == 'OR':
            return evaluate(node.left, d) or evaluate(node.right, d)
    elif isinstance(node, Condition):
        
        if node.op == 'exists':
            # expects node.left_expr to be a Field
            if isinstance(node.left_expr, Field):
                return node.left_expr.name in d
            return False

        # Treat missing fields as None instead of Field instances
        val = eval_expr(node.left_expr, d)
        # If the left expression was a field but not in d, eval_expr returns its name as string fallback.
        # But if it's supposed to be null, we should treat it as None.
        if isinstance(node.left_expr, Field) and node.left_expr.name not in d:
            val = None

        if node.op == 'is_null':
            return val is None or val == ''
            
        target = eval_expr(node.right_expr, d)
        # However, for the RIGHT side, if it's a field not in d, it's very likely just a string literal without quotes!
        # Because we treat unquoted strings as Field(name) and then eval_expr returns `name`.
        # So we don't set target = None here, we keep it as target = name.

        val_str = str(val) if val is not None else ''
        target_str = str(target) if target is not None else ''
        
        # When comparing numeric equality natively, we should try checking numeric values
        # "age = 40" -> 40 == 40.0, but target_str might be "40.0" and val_str "40".
        if node.op in ('=', '!='):
            try:
                val_num = float(val) if val is not None else 0.0
                target_num = float(target) if target is not None else 0.0
                num_equal = (val_num == target_num)
                if node.op == '=': return num_equal or val_str == target_str
                if node.op == '!=': return not num_equal and val_str != target_str
            except (ValueError, TypeError):
                pass

            if node.op == '=':
                return val_str == target_str
            if node.op == '!=':
                return val_str != target_str
        if node.op == '~':
            return target_str in val_str
        if node.op == '=~':
            try:
                return bool(re.search(target_str, val_str))
            except re.error:
                return False
        if node.op == 'in':
            return val_str in target_str.split(',')
        if node.op == 'not in':
            return val_str not in target_str.split(',')
            
        # Numeric comparisons
        try:
            val_num = float(val) if val is not None else 0.0
            target_num = float(target) if target is not None else 0.0
            if node.op == '>': return val_num > target_num
            if node.op == '>=': return val_num >= target_num
            if node.op == '<': return val_num < target_num
            if node.op == '<=': return val_num <= target_num
        except (ValueError, TypeError):
            # Fallback to string comparison
            if node.op == '>': return val_str > target_str
            if node.op == '>=': return val_str >= target_str
            if node.op == '<': return val_str < target_str
            if node.op == '<=': return val_str <= target_str
            
    return False
