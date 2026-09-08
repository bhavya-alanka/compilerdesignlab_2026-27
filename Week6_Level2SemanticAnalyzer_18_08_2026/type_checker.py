"""
TinyCStr Week 6 - Semantic Analysis / Type Checker.

Checks:
1. Undeclared variables
2. Arithmetic type promotion
3. Relational comparisons
4. Ternary expressions
5. Explicit casts
6. Assignments

It also inserts Cast nodes for legal implicit conversions.
"""

from ast_nodes import (
    Const, Var, Assign, Print,
    BinOp, RelOp, Cast, Ternary
)

from SymbolTable import DataType
from type_rules import is_numeric, promote, SemanticError


class TypeChecker:

    def __init__(self, symbol_table):
        self.symbol_table = symbol_table
        self.errors = []

    def add_error(self, message, lineno):
        self.errors.append(SemanticError(message, lineno))

    # ------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------

    def check_function(self, function):

        checked_statements = []

        for stmt in function.getStatementsAstList():

            checked_stmt = self.check_stmt(stmt)

            if checked_stmt is not None:
                checked_statements.append(checked_stmt)

        function.setStatementsAstList(checked_statements)

        return self.errors

    # ------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------

    def check_stmt(self, stmt):

        if isinstance(stmt, Assign):
            return self.check_assign_stmt(stmt)

        elif isinstance(stmt, Print):
            expr, expr_type = self.check_expr(stmt.expr)
            stmt.expr = expr
            return stmt

        return stmt

    # ------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------

    def check_expr(self, node):

        if isinstance(node, Const):
            return node, node.type

        elif isinstance(node, Var):
            return self.check_var(node)

        elif isinstance(node, BinOp):
            return self.check_binop(node)

        elif isinstance(node, RelOp):
            return self.check_relop(node)

        elif isinstance(node, Cast):
            return self.check_cast(node)

        elif isinstance(node, Ternary):
            return self.check_ternary(node)

        return node, None

    # ------------------------------------------------------------
    # Variable checking
    # ------------------------------------------------------------

    def check_var(self, node):

        entry = self.symbol_table.getSymbol(node.name)

        if entry is None:
            self.add_error(
                f"undeclared variable '{node.name}'",
                node.lineno
            )
            return node, None

        return node, entry.getDataType()

    # ------------------------------------------------------------
    # Arithmetic operators
    # ------------------------------------------------------------

    def check_binop(self, node):

        left, left_type = self.check_expr(node.left)
        right, right_type = self.check_expr(node.right)

        node.left = left
        node.right = right

        # Stop additional errors if one variable was undeclared
        if left_type is None or right_type is None:
            return node, None

        # Both operands must be numeric
        if not is_numeric(left_type) or not is_numeric(right_type):

            self.add_error(
                f"arithmetic operator '{node.op}' requires numeric operands",
                node.lineno
            )

            return node, None

        result_type = promote(left_type, right_type)

        # Insert implicit casts
        if left_type != result_type:
            node.left = Cast(
                result_type,
                node.left,
                lineno=node.left.lineno
            )

        if right_type != result_type:
            node.right = Cast(
                result_type,
                node.right,
                lineno=node.right.lineno
            )

        return node, result_type

    # ------------------------------------------------------------
    # Relational operators
    # ------------------------------------------------------------

    def check_relop(self, node):

        left, left_type = self.check_expr(node.left)
        right, right_type = self.check_expr(node.right)

        node.left = left
        node.right = right

        if left_type is None or right_type is None:
            return node, None

        # Numeric comparisons
        if is_numeric(left_type) and is_numeric(right_type):

            common_type = promote(left_type, right_type)

            if left_type != common_type:
                node.left = Cast(
                    common_type,
                    node.left,
                    lineno=node.left.lineno
                )

            if right_type != common_type:
                node.right = Cast(
                    common_type,
                    node.right,
                    lineno=node.right.lineno
                )

            return node, DataType.INT

        # String equality comparison only
        if left_type == DataType.STRING and right_type == DataType.STRING:

            if node.op in ('==', '!='):
                return node, DataType.INT

        self.add_error(
            f"incompatible types for comparison '{node.op}'",
            node.lineno
        )

        return node, None

    # ------------------------------------------------------------
    # Explicit casts
    # ------------------------------------------------------------

    def check_cast(self, node):

        expr, expr_type = self.check_expr(node.expr)

        node.expr = expr

        if expr_type is None:
            return node, None

        target_type = node.target_type

        # Numeric conversions are allowed
        if is_numeric(expr_type) and is_numeric(target_type):
            return node, target_type

        # Same-type cast is also allowed
        if expr_type == target_type:
            return node, target_type

        self.add_error(
            f"invalid cast from {expr_type.name} to {target_type.name}",
            node.lineno
        )

        return node, None

    # ------------------------------------------------------------
    # Ternary operator
    # ------------------------------------------------------------

    def check_ternary(self, node):

        cond, cond_type = self.check_expr(node.cond)
        then_expr, then_type = self.check_expr(node.then_expr)
        else_expr, else_type = self.check_expr(node.else_expr)

        node.cond = cond
        node.then_expr = then_expr
        node.else_expr = else_expr

        if cond_type is not None:

            if not is_numeric(cond_type):
                self.add_error(
                    "ternary condition must be numeric",
                    node.cond.lineno
                )

        if then_type is None or else_type is None:
            return node, None

        # Same type
        if then_type == else_type:
            return node, then_type

        # Both numeric -> promote
        if is_numeric(then_type) and is_numeric(else_type):

            result_type = promote(then_type, else_type)

            if then_type != result_type:
                node.then_expr = Cast(
                    result_type,
                    node.then_expr,
                    lineno=node.then_expr.lineno
                )

            if else_type != result_type:
                node.else_expr = Cast(
                    result_type,
                    node.else_expr,
                    lineno=node.else_expr.lineno
                )

            return node, result_type

        self.add_error(
            f"incompatible ternary branch types "
            f"{then_type.name} and {else_type.name}",
            node.lineno
        )

        return node, None

    # ------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------

    def check_assign_stmt(self, node):

        # Check the variable being assigned to
        entry = self.symbol_table.getSymbol(node.var.name)

        if entry is None:

            self.add_error(
                f"undeclared variable '{node.var.name}'",
                node.var.lineno
            )

            # Still check RHS so other errors can be found
            expr, expr_type = self.check_expr(node.expr)
            node.expr = expr

            return node

        target_type = entry.getDataType()

        expr, expr_type = self.check_expr(node.expr)
        node.expr = expr

        if expr_type is None:
            return node

        # Same type
        if target_type == expr_type:
            return node

        # Numeric conversion
        if is_numeric(target_type) and is_numeric(expr_type):

            # Insert Cast
            node.expr = Cast(
                target_type,
                node.expr,
                lineno=node.expr.lineno
            )

            return node

        # Anything involving STRING is incompatible
        self.add_error(
            f"cannot assign {expr_type.name} to {target_type.name}",
            node.lineno
        )

        return node


# ----------------------------------------------------------------
# Program-level helper used by main.py
# ----------------------------------------------------------------

def check_program(program):

    all_errors = []

    for function in program.getFunctions():

        checker = TypeChecker(function.getLocalSymbolTable())

        errors = checker.check_function(function)

        all_errors.extend(errors)

    return all_errors
