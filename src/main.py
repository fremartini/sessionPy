if __name__ == '__main__':
    from typing import List

    from lexer import Lexer
    from parser import Parser
    from projector import Projector


    def run(file: str) -> List[str] | str:
        tokens = Lexer(file).lex()
        ast = Parser(tokens).parse()
        return Projector().project(ast)


    files = run('../programs/progs.scr')
    for f in files:
        run(f)