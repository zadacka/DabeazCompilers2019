# hello_llvm.py
from llvmlite.ir import (
    Module, Function, FunctionType, IntType, IRBuilder, Constant
    )

mod = Module('hello')
int_type = IntType(32)
hello_func = Function(mod, FunctionType(int_type, []), name='hello')
block = hello_func.append_basic_block('entry')
builder = IRBuilder(block)
builder.ret(Constant(IntType(32), 37))
print(mod)