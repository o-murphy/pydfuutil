import ast
import inspect
from collections import ChainMap
from textwrap import dedent

import usb.core


def func2():
    raise ValueError

def func1():
    func2()


def get_exceptions_raised(func, seen=None):
    if seen is None:
        seen = set()
    exceptions = set()

    # Avoid infinite recursion by tracking already seen functions
    if func in seen:
        return exceptions
    seen.add(func)

    # Inspect the function's docstring
    if func.__doc__:
        doc_lines = func.__doc__.split('\n')
        for line in doc_lines:
            if "Raises" in line:
                exceptions.update(line.split(":")[1].strip().split(","))

    # Inspect the function's code
    source_lines, _ = inspect.getsourcelines(func)
    for line in source_lines:
        if "raise" in line:
            exception_name = line.split("raise")[1].split("(")[0].strip()
            exceptions.add(exception_name)

    # Inspect inner calls
    frame = inspect.currentframe()
    try:
        inner_funcs = [frame.f_globals.get(name) for name in func.__code__.co_names if frame.f_globals.get(name) is not None]
        for inner_func in inner_funcs:
            if inspect.isfunction(inner_func):
                exceptions.update(get_exceptions_raised(inner_func, seen))
    finally:
        del frame

    print(func.__name__, exceptions)
    return exceptions


def calls_c_functions(func, seen=None):
    if seen is None:
        seen = set()
    print(func.__name__)
    c_modules = ['_ctypes', 'builtins', 'sys', 'os', 'posix', 'nt', 'marshal', 'zipimport', 'select', 'itertools',
                 'math']

    for name, module in func.__globals__.items():
        if hasattr(module, '__file__') and module.__file__.endswith('.pyd'):
            return True  # Функція викликає функції з модуля C
        if hasattr(module, '__name__') and module.__name__ in c_modules:
            return True  # Функція викликає вбудовані функції

    seen.add(func)

    # Інспектуємо внутрішні функції
    for name, inner_func in func.__globals__.items():
        if inspect.isfunction(inner_func) and inner_func not in seen:
            if calls_c_functions(inner_func, seen):
                return True

    return False  # Функція не викликає C-функції


def get_exceptions(func, ids=set()):
    try:
        vars = ChainMap(*inspect.getclosurevars(func)[:3])
        source = dedent(inspect.getsource(func))
    except TypeError:
        return

    class _visitor(ast.NodeTransformer):
        def __init__(self):
            self.nodes = []
            self.other = []

        def visit_Raise(self, n):
            self.nodes.append(n.exc)

        def visit_Expr(self, n):
            if not isinstance(n.value, ast.Call):
                return
            c, ob = n.value.func, None
            if isinstance(c, ast.Attribute):
                parts = []
                while getattr(c, 'value', None):
                    parts.append(c.attr)
                    c = c.value
                if c.id in vars:
                    ob = vars[c.id]
                    for name in reversed(parts):
                        ob = getattr(ob, name)

            elif isinstance(c, ast.Name):
                if c.id in vars:
                    ob = vars[c.id]

            if ob is not None and id(ob) not in ids:
                self.other.append(ob)
                ids.add(id(ob))

    v = _visitor()
    v.visit(ast.parse(source))
    for n in v.nodes:
        if isinstance(n, (ast.Call, ast.Name)):
            name = n.id if isinstance(n, ast.Name) else n.func.id
            if name in vars:
                yield func.__name__, n, vars[name]

    for o in v.other:
        yield from get_exceptions(o)


# # Get exceptions raised by the function
# get_exceptions_raised(func1)
# print(calls_c_functions(func1))
# get_exceptions_raised(usb.core.Device.ctrl_transfer)
# print(calls_c_functions(usb.core.Device.ctrl_transfer))


get_exceptions_raised(usb.core.Device.set_interface_altsetting)

