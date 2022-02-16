import inspect
import ast
from ast import *
from typing import *
from textwrap import dedent

def check(f : callable) -> callable:
    file = dedent(inspect.getfile(f))         
    src = _read_src_from_file(file)
    tree = parse(src)
    TypeChecker(tree)
    return f

def _read_src_from_file(file) -> Str:
    with open(file, "r") as f:
        return f.read()

def dump_ast(s, node) -> None:
    print(f'{s}\n', dump(node, indent=4))

def str_to_typ(s : str) -> type:
    # TODO(Johan): There *must* be a better way, Lord have mercy on us!
    match s:
        case 'int': return int
        case 'str': return str
        case 'float': return float
        case 'bool': return bool
        case _: raise Exception(f"unknown type {s}")

class UnionError(Exception):
    ...
"""
TODO: Delete, but keep for now
def union(t1: type, t2: type) -> type:
    if t1 == t2: return t1
    match t1, t2:
        case (typ1, typ2) if typ1 is int and typ2 is int: return int
        case (typ1, typ2) if typ1 is int and typ2 is float: return float
        case (typ1, typ2) if typ1 is float and typ2 is int: return float
        case (typ1, typ2): raise UnionError(f"Cannot union {typ1} with {typ2}")
"""

# TODO: Enforce subtyping, i.e. List[int] <: List[float]
# Currently a problem due to typing's constructs != type
def union(t1: type, t2: type) -> type:
    if t1 == t2: return t1
    numerics : List[type] = [float, complex, int, bool, Any] # from high to low
    sequences : List[type] = [str, tuple, bytes, list, bytearray, Any]
    type_hierarchies = [numerics, sequences]
    for typ_hierarcy in type_hierarchies:
        if t1 in typ_hierarcy and t2 in typ_hierarcy:
            for typ in typ_hierarcy:
                if t1 == typ or t2 == typ: 
                    return typ
    # TODO: Subtyping of parameterized types, List[int] <: List[float]
    # TODO: What to do with more complex structures, i.e. Dict[X,Y] or Tuple[X,Y]?
    # if isinstance(type(t1), list) and isinstance(type(t2), list):
    #     t1 = get_args(t1)[0]
    #     t2 = get_args(t2)[0]
    #     return List [ union(t1, t2) ]
    else:
        return t1 if issubclass(t1, t2) else t2

class TypeChecker(NodeVisitor):
    def __init__(self, tree) -> None:
        self.environments : List[Dict[str, type | List[type]]] = [{}] 
        self.visit(tree)

    def visit_Module(self, node: Module) -> None:
        for stmt in node.body:
            self.visit(stmt)

    def visit_FunctionDef(self, node: FunctionDef) -> None:
        return_type : type = Any if not node.returns else str_to_typ(self.visit(node.returns))
        parameter_types : List[Tuple[str, type]] = self.visit(node.args)
        parameter_types = [ty for (_,ty) in parameter_types]
        parameter_types.append(return_type)
        self.bind(node.name, parameter_types)

        self.dup()
        
        args = self.visit(node.args)
        for pair in args:
            v, t = pair
            self.bind(v, t)

        for stmt in node.body:
            match stmt:
                case stmt if isinstance(stmt, Return):
                    actual_return_type = self.visit(stmt)
                    self.fail_if((not return_type == Any) and actual_return_type != return_type, f'expected return type {return_type} got {actual_return_type}')
                case _: self.visit(stmt)

        self.pop()

    def visit_arguments(self, node: arguments) -> List[Tuple[str, type]]:
        arguments = []
        for arg in node.args:
            arguments.append(self.visit_arg(arg))
        return arguments

    def visit_arg(self, node: arg) -> Tuple[str, type]:
        match node:
            case node if node.annotation:
                ann : str = self.visit(node.annotation)
                ann_typ : type = str_to_typ(ann)
                return (node.arg, ann_typ)
            case _:
                return (node.arg, Any)

    def visit_Name(self, node: Name) -> Str:
        # TODO: consider return (node.id, lookup(node.id)) to easily pass types around
        return node.id

    def visit_Assign(self, node: Assign) -> None:
        #FIXME: handle case where node.targets > 1
        assert(len(node.targets) == 1)

        target : str = self.visit(node.targets[0])
        value : type = self.visit(node.value)
        self.bind(target, value)

    def visit_AnnAssign(self, node: AnnAssign) -> None:
        target : str = self.visit(node.target)
        ann_type : Type = str_to_typ(self.visit(node.annotation))
        rhs_type : Type = self.visit(node.value)
        self.fail_if(not ann_type == rhs_type, f'annotated type {ann_type} does not match inferred type {rhs_type}')

        self.bind(target, ann_type)

    def op_to_str(self, op):
        match type(op):
            case ast.Add: return "__add__"
            case ast.Sub: return "__sub__"
            case ast.Mult: return "__mul__"

    def visit_BinOp(self, node: BinOp) -> type:
        op_str = self.op_to_str(node.op)
        if not hasattr(node.left, op_str):
            return Exception(f"left operand does not support {op_str}")
        if not hasattr(node.right, op_str):
            return Exception(f"right operand does not support {op_str}")
        match (node.left):
            case left if isinstance(left, Name): l = self.lookup(self.visit(left))
            case left: l = self.visit(left)

        match (node.right):
            case right if isinstance(right, Name): r = self.lookup(self.visit(right))
            case right: r = self.visit(right)
        return union(l, r)

    def visit_Constant(self, node: Constant) -> type:
        return type(node.value)

    def visit_Call(self, node: Call) -> Any:
        def _class_def():
            self.bind(self.visit(node.func), ClassVar)
            return ClassVar

        def _call():
            name : str = self.visit(node.func)
            args_typs : List[type] = []
            for arg in node.args:
                match arg:
                    case arg if isinstance(arg, Name):
                        args_typs.append(self.lookup(self.visit(arg)))
                    case _: 
                        args_typs.append(self.visit(arg))

            expected_args : List[type] = self.lookup(name)
            return_type : type = expected_args.pop()
            
            well_typed = args_typs == expected_args

            self.fail_if(not len(args_typs) == len(expected_args), f'')

            self.fail_if(not well_typed, f'function {name} expected {expected_args}, got {args_typs}')

            return return_type

        match node:
            case _ if self.lookup(self.visit(node.func)) == ClassDef: return _class_def()
            case _: _call()
                
    
    def visit_Return(self, node: Return) -> Type:
        match node:
            case node if isinstance(node.value,Name): return self.lookup(self.visit(node.value))
            case _: return self.visit(node.value)

    def visit_ClassDef(self, node: ClassDef) -> None:
        self.bind(node.name, ClassDef)

    def push(self) -> None:
        self.environments.append({})

    def dup(self) -> None:
        self.environments.append(self.get_latest_scope())

    def pop(self) -> None:
        self.environments.pop()

    def lookup(self, key) -> Type:
        latest_scope : Dict[str, type] = self.get_latest_scope()
        self.fail_if(key not in latest_scope, f'{key} was not found in {latest_scope}')
        return latest_scope[key]  
        
    def get_latest_scope(self) -> Dict[str, type]:
        return self.environments[len(self.environments)-1]

    def bind(self, var: str, typ: type) -> None:
        latest_scope : Dict[str, type] = self.get_latest_scope()
        latest_scope[var] = typ

    def fail_if(self, e : bool, msg : str) -> None:
        if (e): raise Exception(msg)

    def print_envs(self) -> None:
        print(self.environments)