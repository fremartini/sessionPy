import ast
from infer import infer
from enum import Enum
from util import channels_str
class Scope(Enum):
    LEFT = 0
    RIGHT = 1
    NORMAL = 2

class Checker(ast.NodeVisitor):
    def __init__(self, tree, functions, channels):
        self.tree = tree
        self.functions = functions
        self.channels = channels
        self.scope = Scope.NORMAL

    def get_channel_name_scope(self, ch_name : str) -> str:
        key = ch_name
        match self.scope:
            case Scope.LEFT: 
                key = f'{ch_name}_LEFT'
            case Scope.RIGHT: 
                key = f'{ch_name}_RIGHT'
        return key



    def run(self):
        self.visit(self.tree)
        self.verify_postconditions()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        for dec in node.decorator_list:
            if dec.id == 'verify_channels': 
                self.verify_channels(node.body)

    def verify_channels(self, stmts):
        for stmt in stmts:
            match stmt:
                case ast.Expr(): self.check_expr(stmt)
                case ast.Assign(): self.check_assign(stmt)
                case ast.Match(): self.check_match(stmt)
                case ast.If(): self.check_if(stmt)

    def check_match(self, match):
        assert(isinstance(match, ast.Match))

        if self.is_channel_offer(match.subject):
            ch_name = match.subject.func.value.id
            cases = match.cases
            assert len(cases) == 2
            for case in cases:
                pattern = case.pattern
                body = case.body
                # st = self.get_session_type(ch_name)
                att = pattern.value
                if att.attr == 'LEFT':
                    key = f'{ch_name}_LEFT'
                    self.channels[key] = self.channels[ch_name].left
                    self.verify_channels(body)
                    self.scope = Scope.LEFT
                elif att.attr == 'RIGHT':
                    key = f'{ch_name}_RIGHT'
                    self.channels[key] = self.channels[ch_name].right
                    self.verify_channels(body)
                    self.scope = Scope.RIGHT

            self.channels[ch_name] = self.channels[ch_name].right

    # checks <predX(x) and attr.y == y>
    def check_attribute(self, att, predX, y): 
        assert(isinstance(att, ast.Attribute))
        assert(isinstance(att.value, ast.Name))
        return predX(att.value.id) and att.attr == y

    def is_channel_offer(self, subject):
        return (isinstance(subject, ast.Call) and 
                isinstance(subject.func, ast.Attribute) and
                self.check_attribute(subject.func, lambda x: x in self.channels, 'offer'))

    def check_if(self, expr):
        body = expr.body
        orelse = expr.orelse

        self.verify_channels(body)
        self.scope = Scope.NORMAL
        self.verify_channels(orelse)

    def check_expr(self, expr):
        assert(isinstance(expr, ast.Expr))
        if isinstance(expr.value, ast.Call):
            self.check_call(expr.value)

    """
    In this function, we check for following two scenarios: 
     * ch = Channel...
     * <var> = ch.send/recv
    First, if we assign a channel to a variable, our dictionary should be updated with session type.
    Second, if some variable is assigned to a call to our channel, we should progress ST/validate types.
    """
    def check_assign(self, asgn):
        assert(isinstance(asgn, ast.Assign))
        _, v = *asgn.targets, asgn.value 
        if isinstance(v, ast.Call):
            self.check_call(v)

    """
        Extracts type and method for a a call object right now ASSUMED to be a
        channel.  
        
        Examples: 
         * ch.send(42) or ch.send(f())
         * c.recv() 

        In the first case, we need to validate that type of argument (42, f())
        matches the current action and type of our session type.  
    """
    def check_call(self, call):
        assert(isinstance(call, ast.Call))
        call_func = call.func
        call_args = call.args
        if(isinstance(call_func, ast.Attribute)):       # this structure: x.y()
                                                        #                 ^ attribute
            ch_name = self.get_channel_name_scope(call_func.value.id) 
            op = call_func.attr
            st = self.channels[ch_name]
            match op:
                case 'choose':
                    print('Scope', self.scope, 'in call to choose, current channels:\n', channels_str(self.channels))
                    assert(len(call_args) == 1)
                    arg = call_args[0]
                    if not st:
                        raise Exception(f"{ch_name} has been exhausted of operations")

                    assert(arg.value.id == 'Branch')
                    left_or_right = arg.attr
                    assert left_or_right in ['LEFT', 'RIGHT']
                    self.scope = Scope.LEFT if left_or_right == 'LEFT' else Scope.RIGHT
                    ch_name = self.get_channel_name_scope(ch_name)
                    self.channels[ch_name] = st.left if self.scope == Scope.LEFT else st.right
                    print('CHANNELS:\n', self.channels)
                case 'send':
                    print('Scope', self.scope, 'in call to SEND, current channels:\n', channels_str(self.channels))
                    assert(len(call_args) == 1)
                    arg_typ = infer(call_args[0])
                    if not st:
                        raise Exception(f"{ch_name} has been exhausted of operations")
                    assertEq(st.typ, arg_typ)
                    assertEq(st.action, op)
                    self.channels[ch_name] = st.right
                case 'recv':
                    print('Scope', self.scope, 'in call to RECV, current channels:\n', channels_str(self.channels))
                    assert(len(call_args) == 0)
                    if not st:
                        raise Exception(f"{ch_name} has been exhausted of operations")
                    assertEq(st.action, op)
                    self.channels[ch_name] = st.right
        elif isinstance(call_func, ast.Name): # structure: print(), f(), etc.
                                              #            ^^^^^    ^ - Name
            func_name = call.func.id

            for idx, arg in enumerate(call_args):
                if isinstance(arg, ast.Name) and arg.id in self.channels: 
                    func = self.functions[func_name]
                    func_chan_arg = func.args.args[idx].arg

                    self.channels[func_chan_arg] = self.channels[arg.id]
                    self.verify_channels(func.body)
                    self.channels[arg.id] = self.channels[func_chan_arg]
                    self.channels.pop(func_chan_arg)

    def verify_postconditions(self):
        """ 
        If a session-type list is not empty, it has not been used in
        accordance with its type: throw error.  
        """
        errors = []
        print('final channels:\n', channels_str(self.channels))
        for ch_name, ch_ops in self.channels.items():
            if ch_ops:
                errors.append(f'channel "{ch_name}" is not exhausted, missing: {self.channels[ch_name]}')

        if errors:
            raise Exception (f"ill-typed program: {errors}")

def assertEq(expected, actual):
    if (not expected == actual):
        raise Exception("expected " + str(expected) + ", found " + str(actual))