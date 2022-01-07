from typing import List, Callable
from mistql.runtime_value import RuntimeValue, RuntimeValueType
from mistql.expression import (
    Expression,
    RefExpression,
    FnExpression,
    ValueExpression,
    ArrayExpression,
    ObjectExpression,
    PipeExpression,
)
from mistql.stack import Stack
from mistql.builtins import FunctionDefinitionType, builtins
from mistql.stack import add_runtime_value_to_stack, build_initial_stack, find_in_stack
from mistql.expression import BaseExpression

from typeguard import typechecked


@typechecked
def execute_fncall(head: Expression, arguments: List[Expression], stack: Stack):
    fn = execute(head, stack)
    if fn.type != RuntimeValueType.Function:
        raise Exception(f"Tried to call a non-function: {fn}")
    # Not enforced, but definitely should be.
    function_definition: FunctionDefinitionType = fn.value
    return function_definition(arguments, stack, execute)


@typechecked
def execute_pipe(stages: List[Expression], stack: Stack) -> RuntimeValue:
    first: Expression = stages[0]
    remaining: List[Expression] = stages[1:]
    data = execute(first, stack)

    for stage_ast in remaining:
        new_stack = add_runtime_value_to_stack(data, stack)
        fn: Expression
        args: List[Expression]
        if isinstance(stage_ast, FnExpression):
            fn = stage_ast.fn
            args = stage_ast.args.copy()
        else:
            fn = stage_ast
            args = []
        args.append(ValueExpression(data))
        stage = FnExpression(fn, args)
        data = execute(stage, new_stack)

    return data

@typechecked
def execute(ast: Expression, stack: Stack) -> RuntimeValue:
    if not isinstance(ast, BaseExpression):
        raise Exception(f"Expected to evaluate an expression, got {ast}")
    if isinstance(ast, ValueExpression):
        return ast.value
    elif isinstance(ast, RefExpression):
        return find_in_stack(stack, ast.name, ast.absolute)
    elif isinstance(ast, FnExpression):
        return execute_fncall(ast.fn, ast.args, stack)
    elif isinstance(ast, ArrayExpression):
        return RuntimeValue.of([execute(item, stack) for item in ast.items])
    elif isinstance(ast, ObjectExpression):
        return RuntimeValue.of(
            {key: execute(value, stack) for key, value in ast.entries.items()}
        )
    elif isinstance(ast, PipeExpression):
        return execute_pipe(ast.stages, stack)
    raise NotImplementedError("execute() not implemented for " + ast.type)


def execute_outer(ast: Expression, data: RuntimeValue) -> RuntimeValue:
    return execute(ast, build_initial_stack(data, builtins))
