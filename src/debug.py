from ast import dump


def debug_print(*args) -> None:
    debug = not not not True
    if debug:
        print(*args)
        print()


def dump_ast(s, node) -> None:
    print(f'{s}\n', dump(node, indent=4))


def is_a(obj):
    print(obj, 'is a', type(obj))
