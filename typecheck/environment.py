from __future__ import annotations
from enum import Enum
from operator import mod
from lib import *
from debug import debug_print
from typing import Union, List


class Category(Enum):
    VARIABLE = 0
    FUNCTION = 1
    NESTED = 2


def empty() -> dict:
    return {env_typ: {} for env_typ in list(Category)}


class Environment():
    def __init__(self, env=None):
        if env == None:
            env = empty()
        self.environment = env
        
    def lookup_var(self, v: str) -> Typ:
        if v in self.environment[Category.VARIABLE]:
            return self.environment[Category.VARIABLE][v] 
        else:
            raise EnvironmentError(f'{v} not found in {self.environment[Category.VARIABLE]}')

    def lookup_func(self, f: str) -> Typ:
        return self.environment[Category.FUNCTION][f]

    def lookup_nested(self, f: str) -> Environment:
        return self.environment[Category.NESTED][f]

    def lookup_or_default(self, k : str) -> Union[Typ, dict[str, Typ], str]:
        try:
            return self.lookup(k)
        except EnvironmentError:
            return k

    def lookup_var_or_default(self, k : str) -> Union[Typ, dict[str, Typ], str]:
        try:
            return self.lookup_var(k)
        except EnvironmentError:
            return k

    def contains_nested(self, k : str) -> bool:
        return k in self.environment[Category.NESTED]
    
    def bind_var(self, var: str, typ: Typ) -> None:
        self.environment[Category.VARIABLE][var] = typ

    def bind_func(self, f : str, typ: Typ) -> None:
        self.environment[Category.FUNCTION][f] = typ

    def bind_nested(self, key: str, env: Environment) -> None:
        self.environment[Category.NESTED][key] = env
        
    def lookup(self, key : str) -> Typ:
        debug_print(f'lookup: searching for key="{key}" in {self.environment}')
        priority = [Category.VARIABLE, Category.FUNCTION, Category.NESTED]
        for env_cat in priority:
            if key in self.environment[env_cat]:
                return self.environment[env_cat][key]
        raise EnvironmentError(f"'{key}' was not found in {self.environment}")

    def __str__(self) -> str:
        res = "{"
        for key in self.environment:
            res += f'  {key}={self.environment[key]}  '
        return res + "}"

    def __repr__(self):
        return self.__str__()