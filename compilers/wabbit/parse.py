# parse.py
#
# Wabbit parser.   This needs to construct the data model or 
# an abstract syntax tree.    The Grammar here is specified 
# as a PEG (Parsing Expression Grammar)
#
# PEG Syntax:
#
#    'quoted'   : Literal text
#    ( ... )    : Grouping
#      e?       : Optional (0 or 1 matches of e)
#      e*       : Repetition (0 or more matches of e)
#      e+       : Repetition (1 or more matches)
#     e1 e2     : Match e1 then match e2 (sequence)
#    e1 / e2    : Try to match e1. On failure, try to match e2.
#
# Names in all-caps are assumed to be tokens from the tokenize.py file. 
#
# program <- statement* EOF
#
# statement <- assignment
#           /  vardecl
#           /  funcdel
#           /  if_stmt
#           /  while_stmt
#           /  break_stmt
#           /  continue_stmt
#           /  return_stmt
#           /  print_stmt
#
# assignment <- location '=' expression ';'
#
# vardecl <- ('var'/'const') ID type? ('=' expression)? ';'
#
# funcdecl <- 'import'? 'func' ID '(' parameters ')' type '{' statement* '}'
#
# if_stmt <- 'if' expression '{' statement* '}'
#         /  'if' expression '{' statement* '}' else '{' statement* '}'
#
# while_stmt <- 'while' expression '{' statement* '}'
#
# break_stmt <- 'break' ';'
#
# continue_stmt <- 'continue' ';'
#
# return_stmt <- 'return' expression ';'
#
# print_stmt <- 'print' expression ';'
#
# parameters <- ID type (',' ID type)*
#            /  empty
#
# type <- 'int' / 'float' / 'char' / 'bool'
#
# location <- ID
#          /  '`' expression
#
# expression <- orterm ('||' orterm)*
#
# orterm <- andterm ('&&' andterm)*
#
# andterm <- relterm (('<' / '>' / '<=' / '>=' / '==' / '!=') reltime)*
#
# relterm <- addterm (('+' / '-') addterm)*
#
# addterm <- factor (('*' / '/') factor)*
#
# factor <- literal  
#        / ('+' / '-' / '^') expression
#        / '(' expression ')'
#        / type '(' expression ')'
#        / ID '(' arguments ')'
#        / location
#
# arguments <- expression (',' expression)*
#          / empty
#
# literal <- INTEGER / FLOAT / CHAR / bool
#
# bool <- 'true' / 'false
from time import sleep

from compilers.wabbit.check import Variable, Constant, While, Char, Bool
from compilers.wabbit.errors import ParseError
from compilers.wabbit.model import Assignment, BinaryOperator, Integer, Float, NamedLocation, Print, If, \
    UnaryOperator, KNOWN_TYPES
from compilers.wabbit.tokenizer import tokenize


# Special EOF token


class EOF:
    type = 'EOF'
    value = 'EOF'

class Parser:
    """
    Predictive (i.e. peek) Recursive Descent (i.e. recursive calls) Parser
    Also a LL1 Parser: Left to right, Left side first, 1 token ahead
    """
    def __init__(self, tokens):
        self.tokens = tokens    # An iterator that produces a stream of tokens
        self.next_token = None  # one token look-ahead

    def peek(self, *possible):
        # Look ahead at the next token and return it if the type matches one or more possibilities
        # Does not consume the token
        if self.next_token is None:
            self.next_token = next(self.tokens, EOF)

        if self.next_token.type in possible:
            return self.next_token
        else:
            return None

    def expect(self, *possible):
        """ Like peek() but it also consumes the token. Think Pac-Man.  """
        # Return it and consume it
        tok = self.peek(*possible)
        if tok:
            self.next_token = None
            return tok
        else:
            raise ParseError(f"Nope! Looking for {possible} but next token is {next(self.tokens)}")

    # Grammar:
    def parse_assignment(self):
        """assignment := Name '= expr ';'"""
        name = self.expect('NAME')
        self.expect('ASSIGN')
        expression = self.parse_expr()
        self.expect('SEMI')
        return Assignment(NamedLocation(name.value), expression)  # Data Model

    def parse_expr(self):
        """expr := term {'+' | '-' term }"""
        term = self.parse_term()
        while self.peek('PLUS', 'MINUS', 'LT', 'GT', 'LE', 'GE'):
            op = self.expect('PLUS', 'MINUS', 'LT', 'GT', 'LE', 'GE')
            right_term = self.parse_term()
            term = BinaryOperator(op.value, term, right_term)
        return term

    def parse_term(self):
        """term := factor { '*', | '/' factor}"""
        term = self.parse_factor()
        while self.peek('TIMES', 'DIVIDE'):
            op = self.expect('TIMES', 'DIVIDE')
            right_term = self.parse_term()
            term = BinaryOperator(op.value, term, right_term)
        return term

    def parse_factor(self):
        # factor: INTEGER | FLOAT
        if self.peek('INT'):
            # Tokens only have strings. The .value attribute is the matched text.
            # You might have to to run it into a proper integer for the model
            return Integer(int(self.expect('INT').value))
        elif self.peek('FLOAT'):
            return Float(float(self.expect('FLOAT').value))
        elif self.peek('CHAR'):
            return Char(str(self.expect('CHAR').value))
        elif self.peek('BOOL'):
            return Bool(self.expect('BOOL').value)
        elif self.peek('LPAREN'):
            self.expect('LPAREN')
            expression = self.parse_expr()
            self.expect('RPAREN')
            return expression
        elif self.peek('MINUS', 'PLUS'):
            op = self.expect('MINUS', 'PLUS')
            expr = self.parse_expr()
            return UnaryOperator(op.value, expr)
        elif self.peek('NAME'):
            expr = self.expect('NAME')
            return NamedLocation(expr.value)
        else:
            raise ParseError('Bad factor ... reached the end but nothing found')

    # print expression ;
    def parse_print(self):
        self.expect('PRINT')
        expr = self.parse_expr()
        self.expect('SEMI')
        return Print(expr)

    # if test {consequences } else {alternative}
    def parse_if(self):
        self.expect('IF')
        test = self.parse_expr()
        self.expect('LBRACE')
        consequence = self.parse_statements()
        self.expect('RBRACE')
        if self.peek('ELSE'):
            self.expect('ELSE')
            self.expect('LBRACE')
            alternative = self.parse_statements()
            self.expect('RBRACE')
        else:
            alternative = []
        return If(test, consequence, alternative)

    def parse_statements(self):
        statements = []
        while not self.peek('EOF', 'RBRACE'):
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
            else:
                break
        return statements

    # var declaration: (var | const) name [type] [= expr] ;
    def parse_var(self):
        decl = self.expect('VAR', 'CONST').type
        name = self.expect('NAME').value
        if self.peek('NAME'):
            type = self.parse_type()
        else:
            type = None
        if self.peek('ASSIGN'):
            self.expect('ASSIGN')
            expr = self.parse_expr()
        else:
            expr = None
        self.expect('SEMI')
        if decl == 'VAR':
            return Variable(name, expr, type)
        else:
            return Constant(name, expr, type)

    # type declaration: (int | float | bool | char)
    def parse_type(self):
        tok = self.expect('NAME')
        if tok.value in KNOWN_TYPES:
            return tok.value
        else:
            raise ParseError(f'Expected a type when parsing {tok}')

    def parse_statement(self):
        if self.peek('PRINT'):
            return self.parse_print()
        elif self.peek('IF'):
            return self.parse_if()
        elif self.peek('WHILE'):
            return self.parse_while()
        elif self.peek('CONST', 'VAR'):
            return self.parse_var()
        elif self.peek('NAME'):
            return self.parse_assignment()
        else:
            raise ParseError(f'parse_statement failed to handle {self.next_token}')

    def parse_while(self):
        self.expect('WHILE')
        test = self.parse_expr()
        self.expect('LBRACE')
        consequence = self.parse_statements()
        self.expect('RBRACE')
        return While(test, consequence)


if __name__ == '__main__':
    print(list(tokenize("print 10;")))
    tokens = tokenize("print 10;")
    sleep(0.1)
    parser = Parser(tokens)
    tokenized = parser.parse_statements()

    for x in tokenized:
        print(x)
