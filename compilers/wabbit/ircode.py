# ircode.py
'''
A Intermediate "Virtual" Machine
================================
An actual CPU typically consists of registers and a small set of basic
opcodes for performing mathematical calculations, loading/storing
values from memory, and basic control flow (branches, jumps, etc.).
Although you can make a compiler generate instructions directly for a
CPU, it is often simpler to target a higher-level of abstraction
instead.  One such abstraction is that of a stack machine. 

For example, suppose you want to evaluate an operation like this:

    a = 2 + 3 * 4 - 5

To evaluate the above expression, you could generate
pseudo-instructions like this instead:

    CONSTI 2      ; stack = [2]
    CONSTI 3      ; stack = [2, 3]
    CONSTI 4      ; stack = [2, 3, 4]
    MULI          ; stack = [2, 12]
    ADDI          ; stack = [14]
    CONSTI 5      ; stack = [14, 5]
    SUBI          ; stack = [9]
    STORE "a"     ; stack = []

Notice how there are no details about CPU registers or anything like
that here. It's much simpler (a lower-level module can figure out the
hardware mapping later if it needs to).

CPUs usually have a small set of code datatypes such as integers and
floats.  There are dedicated instructions for each type.  The IR code
will follow the same principle by supporting integer and floating
point operations. For example:

    ADDI   ; Integer add
    ADDF   ; Float add

Although the input language might have other types such as 'bool' and
'char', those types need to be mapped down to integers or floats. For
example, a bool can be represented by an integer with values {0, 1}. A
char can be represented by an integer whose value is the same as
the character code value (i.e., an ASCII code or a Unicode code-point).

With that in mind, here is a basic instruction set for our IR Code:

    ; Integer operations
    CONSTI  value            ; Push a integer literal on the stack
    GLOBALI name             ; Declare an integer global variable 
    LOCALI name              ; Declare an integer local variable
    ADDI                     ; Add top two items on stack
    SUBI                     ; Substract top two items on stack
    MULI                     ; Multiply top two items on stack
    DIVI                     ; Divide top two items on stack
    ANDI                     ; Bitwise AND
    ORI                      ; Bitwise OR
    LTI                      : <
    LEI                      : <=
    GTI                      : >
    GEI                      : >=
    EQI                      : ==
    NEI                      : !=
    PRINTI                   ; Print top item on stack
    PEEKI                    ; Get integer from memory (address on stack)
    POKEI                    ; Put integer in memory (value, address) on stack.
    ITOF                     ; Convert integer to float

    ; Floating point operations
    CONSTF value             ; Push a float literal
    GLOBALF name             ; Declare a float global variable 
    LOCALF name              ; Declare a float local variable
    ADDF                     ; Add top two items on stack
    SUBF                     ; Substract top two items on stack
    MULF                     ; Multiply top two items on stack
    DIVF                     ; Divide top two items on stack
    LTF                      : <
    LEF                      : <=
    GTF                      : >
    GEF                      : >=
    EQF                      : ==
    NEF                      : !=
    PRINTF                   ; Print top item on stack
    PEEKF                    ; Get float from memory (address on stack)
    POKEF                    ; Put float in memory (value, address on stack) 
    FTOI                     ; Convert float to integer

    ; Byte-oriented operations (values are presented as integers)    
    PRINTB                   ; Print top item on stack
    PEEKB                    ; Get byte from memory (address on stack)
    POKEB                    ; Put byte in memory (value, address on stack)

    ; Variable load/store
    LOAD name                ; Load variable on stack (must be declared already)
    STORE name               ; Save variable from stack (must be declared already)

    ; Function call and return
    CALL name                ; Call function. All arguments must be on stack
    RET                      ; Return from a function. Value must be on stack

    ; Structured control flow
    IF                       ; Start consequence part of an "if". Test on stack
    ELSE                     ; Start alternative part of an "if".
    ENDIF                    ; End of an "if" statement.

    LOOP                     ; Start of a loop
    CBREAK                   ; Conditional break. Test on stack.
    CONTINUE                 ; Go back to loop start
    ENDLOOP                  ; End of a loop

    ; Memory
    GROW                     ; Increment memory (size on stack) (returns new size)

One word about memory access... the PEEK and POKE instructions are
used to access raw memory addresses.  Both instructions require a
memory address to be on the stack first.  For the POKE instruction,
the value being stored is pushed after the address. The order is
important and it's easy to mess it up.  So pay careful attention to
that.

Your Task
=========
Your task is as follows: Write code that walks through the program structure
and flattens it to a sequence of instructions represented as tuples of the
form:

       (operation, operands, ...)

For example, the code at the top might end up looking like this:

    code = [
       ('CONSTI', 2),
       ('CONSTI', 3),
       ('CONSTI', 4),
       ('MULI',),
       ('ADDI',),
       ('CONSTI', 5),
       ('SUBI',),
       ('STOREI', 'a'),
    ]

Functions
=========
All generated code is associated with some kind of function.  For
example, with a user-defined function like this:

    func fact(n int) int {
        var result int = 1;
        var x int = 1;
        while x <= n {
            result = result * x;
            x = x + 1;
        }
     }

You should create a Function object that contains the name of the
function, the arguments, the return type, and a body which contains
all of the low-level instructions.  Note: at this level, the types are
going to represent low-level IR types like Integer (I) and Float (F).
They are not the same types as used in the high-level Wabbit code.

Also, all code that's defined *outside* of a Function should still
go into a function called "_init()".  For example, if you have
global declarations like this:

     const pi = 3.14159;
     const r = 2.0;
     print pi*r*r;

Your code generator should actually treat them like this:

     func _init() int {
         const pi = 3.14159;
         const r = 2.0;
         print pi*r*r;
         return 0;
     }

Bottom line: All code goes into a function.

Modules
=======
The final output of code generation is IR Code for a whole collection
of functions. To produce a final result, put all of the functions in 
some kind of Module object.

GOAL is to take this:
Print(
    BinaryOperator(
        '+',
        Integer(2),
        BinaryOperator(
            '*',
            Integer(3),
            UnaryOperator('-', Integer(4))
        )
    )
and produce this:
[
  CONST, 3
  CONST, 2
  SUBI,
  CONST 2
  MULI
  PRINT
]


'''
from compilers.wabbit.model import Print, Integer, BinaryOperator, Float, UnaryOperator, Constant, Variable, Assignment, \
    NamedLocation, If, While, Char, Bool


class IRFunction:
    def __init__(self, name, parameters, return_type):
        self.name = name
        self.parameters = parameters
        self.return_type = return_type
        self.code = []  # list of IR instructions

    def append(self, instr):
        self.code.append(instr)

# note that IR only has two types: int and float
# func square(x int) int { return x * x }
# square = IRFunction('square', [('x', 'I')], 'I')  # I is the IR code type - integer
# square.append(('LOAD', 'x'))
# square.append(('LOAD', 'x'))
# square.append(('MUL',))
# square.append(('RETURN',))


class IRModule:
    def __init__(self):
        self.functions = {}
        self.code = []

        self.variable_map = {}

    def transpile(self, node):
        if isinstance(node, list):
            for item in node:
                self.transpile(item)
        elif isinstance(node, Print):
            self.transpile_Print(node)
        elif isinstance(node, Integer):
            self.code.append(('CONSTI', node.value))
        elif isinstance(node, Float):
            self.code.append(('CONSTF', node.value))
        elif isinstance(node, Char):
            self.code.append(('CONSTI', ord(node.value)))
        elif isinstance(node, Bool):
            value = 1 if node.value == 'true' else 0
            self.code.append(('CONSTI', value))
        elif isinstance(node, BinaryOperator):
            self.transpile_BinaryOperator(node)
        elif isinstance(node, UnaryOperator):
            self.transpile_UnaryOperator(node)
        elif isinstance(node, Constant):
            self.transpile_ConstantOrVariable(node)
        elif isinstance(node, Variable):
            self.transpile_ConstantOrVariable(node)
        elif isinstance(node, Assignment):
            self.transpile_Assignment(node)
        elif isinstance(node, NamedLocation):
            self.transpile_LoadNamedLocation(node)
        elif isinstance(node, If):
            self.transpile_If(node)
        elif isinstance(node, While):
            self.transpile_While(node)
        else:
            raise ValueError(f"Could not handle '{node}', unknown type")

    def transpile_Print(self, node):
        self.transpile(node.expression)
        if node.expression.type == Integer.type:
            self.code.append(('PRINTI',))
        elif node.expression.type == Float.type:
            self.code.append(('PRINTF',))
        elif node.expression.type == Char.type:
            self.code.append(('PRINTB',))
        else:
            raise ValueError(f'Unhandled (un-print-able) type {node.expression.type}')

    def transpile_UnaryOperator(self, node):
        unaryOpMap = {
            (Integer.type, '-'): [('CONSTI', 0), ('SUBI', )],
            (Float.type,   '-'): [('CONSTF', 0), ('SUBF', )],
        }
        if node.operator == '-':
            instructions = unaryOpMap.get((node.operand.type, node.operator))
            self.code.append(instructions[0])
            self.transpile(node.operand)
            self.code.append(instructions[1])
        elif node.operator == '+':
            self.transpile(node.operand)
        else:
            raise ValueError(f'Operator {node.operator} not supported yet')


    def transpile_BinaryOperator(self, node):
        binaryOpMap = {
            (Integer.type, '+', Integer.type):  'ADDI',
            (Integer.type, '-', Integer.type):  'SUBI',
            (Integer.type, '*', Integer.type):  'MULI',
            (Integer.type, '/', Integer.type):  'DIVI',
            (Integer.type, '<', Integer.type):  'LTI',
            (Integer.type, '>', Integer.type):  'GTI',
            (Integer.type, '<=', Integer.type): 'LEI',
            (Integer.type, '>=', Integer.type): 'GEI',

            (Float.type,   '+', Float.type):    'ADDF',
            (Float.type,   '-', Float.type):    'SUBF',
            (Float.type,   '*', Float.type):    'MULF',
            (Float.type,   '/', Float.type):    'DIVF',
            (Float.type,   '<', Float.type):    'LTF',
            (Float.type,   '>', Float.type):    'GTF',
            (Float.type,   '<=', Float.type):   'LEF',
            (Float.type,   '>=', Float.type):   'GEF',

        }
        self.transpile(node.left)
        self.transpile(node.right)
        opType = binaryOpMap.get((node.left.type, node.operator, node.right.type))
        if opType is None:
            raise ValueError(f'OpType not known for {node.left.type}{node.operator}{node.right.type}')
        self.code.append((opType, ))

    def transpile_ConstantOrVariable(self, node):
        if node.type == Float.type:
            self.code.append(('GLOBALF', node.name))
        elif node.type == Integer.type:
            self.code.append(('GLOBALI', node.name))
        elif node.type == Char.type:
            self.code.append(('GLOBALI', node.name))
        elif node.type == Bool.type:
            self.code.append(('GLOBALI', node.name))
        else:
            raise ValueError(f'Unhandled Const with type {node.type}')

        if node.value:
            self.transpile(node.value)
            self.code.append(('STORE', node.name))

    def transpile_LoadNamedLocation(self, node):
        self.code.append(('LOAD', node.name))

    def transpile_StoreNamedLocation(self, node):
        self.code.append(('STORE', node.name))

    def transpile_Assignment(self, node):
        self.transpile(node.expression)
        self.transpile_StoreNamedLocation(node.location)

    def transpile_If(self, node):
        self.transpile(node.test)
        self.code.append(('IF',))
        self.transpile(node.consequence)
        if node.alternative is not None:
            self.code.append(('ELSE',))
            self.transpile(node.alternative)
        self.code.append(('ENDIF',))

    def transpile_While(self, node):
        self.code.append(('LOOP',))

        self.code.append(('CONSTI', 1))  # Push 1
        self.transpile(node.test)        # Evaluate the test
        self.code.append(('SUBI', ))     # Do '1 - test value' to do a NOT operation on the test
        self.code.append(('CBREAK', ))
        self.transpile(node.consequence)
        self.code.append(('ENDLOOP',))


#         consequence
# alternative


def generate_ircode(code):
    irmodule = IRModule()
    irmodule.transpile(code)
    return irmodule.code
