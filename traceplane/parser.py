import re

class Node:
    pass

class BinOp(Node):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class Condition(Node):
    def __init__(self, field, op, value=None):
        self.field = field
        self.op = op
        self.value = value

def tokenize(expr):
    token_specification = [
        ('STRING',   r'"[^"]*"|\'[^\']*\''),
        ('OP2',      r'=~|!=|>=|<='),
        ('OP_WORD',  r'\b(?:not in|is_null|in|exists)\b'),
        ('OP1',      r'>|<|=|~'),
        ('AND',      r'\band\b'),
        ('OR',       r'\bor\b'),
        ('LPAREN',   r'\('),
        ('RPAREN',   r'\)'),
        ('WORD',     r'[^\s()=~><!]+'),
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
            kind = 'WORD' # Treat strings as just values/words
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
            node = self.parse_or()
            if not self.consume('RPAREN'):
                raise ValueError("Expected ')'")
            return node
            
        # Condition: FIELD OP VALUE
        field_tok = self.consume('WORD')
        if not field_tok:
            raise ValueError(f"Expected field name, got {tok}")
        field = field_tok[1]
        
        op_tok = self.consume('OP1') or self.consume('OP2') or self.consume('OP_WORD')
        if not op_tok:
            raise ValueError(f"Expected operator after {field}, got {self.peek()}")
            
        op = op_tok[1].lower()
        if op in ('exists', 'is_null'):
            return Condition(field, op)
            
        # Otherwise, need a value
        val_tok = self.consume('WORD')
        if not val_tok:
            # Some lists like `in (a, b)`? For simplicity, we assume `in a,b` or just treat value as string.
            # The prompt doesn't specify list syntax, let's just accept comma-separated strings.
            raise ValueError(f"Expected value after operator {op}")
            
        value = val_tok[1]
        return Condition(field, op, value)

def parse_where(expr):
    tokens = tokenize(expr)
    return Parser(tokens).parse()

def evaluate(node, d: dict) -> bool:
    if node is None:
        return True
    if isinstance(node, BinOp):
        if node.op == 'AND':
            return evaluate(node.left, d) and evaluate(node.right, d)
        elif node.op == 'OR':
            return evaluate(node.left, d) or evaluate(node.right, d)
    elif isinstance(node, Condition):
        val = d.get(node.field)
        val_str = str(val) if val is not None else ''
        
        if node.op == 'exists':
            return node.field in d
        if node.op == 'is_null':
            return val is None or val == ''
            
        target = node.value
        
        if node.op == '=':
            return val_str == target
        if node.op == '!=':
            return val_str != target
        if node.op == '~':
            return target in val_str
        if node.op == '=~':
            try:
                return bool(re.search(target, val_str))
            except re.error:
                return False
        if node.op == 'in':
            # assumes target is comma-separated
            return val_str in target.split(',')
        if node.op == 'not in':
            return val_str not in target.split(',')
            
        # Numeric comparisons
        try:
            val_num = float(val) if val is not None else 0.0
            target_num = float(target)
            if node.op == '>': return val_num > target_num
            if node.op == '>=': return val_num >= target_num
            if node.op == '<': return val_num < target_num
            if node.op == '<=': return val_num <= target_num
        except ValueError:
            # Fallback to string comparison
            if node.op == '>': return val_str > target
            if node.op == '>=': return val_str >= target
            if node.op == '<': return val_str < target
            if node.op == '<=': return val_str <= target
            
    return False
