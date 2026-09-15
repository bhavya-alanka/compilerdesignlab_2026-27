"""
TinyCStr -- AST to Three-Address Code (triple form) generator.

Read docs/typed_3ac_reference.md before editing this file.

WEEK 7:
    - RelOp -> RelOpTriple
    - Cast -> CastTriple
    - Ternary -> SelectTriple

The TAC layer remains flat. Branches and labels required for
comparisons and ternary expressions are generated later by
tac_to_mips.py.
"""

from SymbolTable import DataType
from ast_nodes import (
    Const,
    Var,
    Assign,
    Print,
    BinOp,
    RelOp,
    Cast,
    Ternary,
)

from three_address_code import (
    TripleTAC,
    BinOpTriple,
    AssignTriple,
    PrintTriple,
    RelOpTriple,
    CastTriple,
    SelectTriple,
)


class TACGenerator:
    def __init__(self):
        self.program = TripleTAC()

    def generate(self, function):
        """
        Walk all statements in source order and generate TAC.
        """

        for stmt in function.getStatementsAstList():
            self.gen_stmt(stmt)

        return self.program

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def gen_stmt(self, stmt):
        """
        Generate TAC for a statement.
        """

        # --------------------------------------------------------------
        # Assignment
        # --------------------------------------------------------------

        if isinstance(stmt, Assign):
            operand = self.gen_expr(stmt.expr)

            self.program.append(
                AssignTriple(
                    stmt.var.name,
                    operand
                )
            )

        # --------------------------------------------------------------
        # Print
        # --------------------------------------------------------------

        elif isinstance(stmt, Print):
            operand = self.gen_expr(stmt.expr)

            self.program.append(
                PrintTriple(operand)
            )

        else:
            raise ValueError(
                f"unexpected statement type: {type(stmt)}"
            )

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def gen_expr(self, node):
        """
        Generate TAC for an expression.

        Returns either:
            - a variable name
            - a literal string
            - a TripleRef referring to an earlier triple
        """

        # --------------------------------------------------------------
        # Constant
        # --------------------------------------------------------------

        if isinstance(node, Const):

            # String literals need their quote characters preserved so
            # tac_to_mips.py can distinguish them from variable names.
            if node.type == DataType.STRING:
                return f'"{node.value}"'

            # Same for character literals.
            elif node.type == DataType.CHAR:
                return f"'{node.value}'"

            # INT and DOUBLE literals can be represented directly as
            # their textual value.
            else:
                return str(node.value)

        # --------------------------------------------------------------
        # Variable
        # --------------------------------------------------------------

        elif isinstance(node, Var):
            return node.name

        # --------------------------------------------------------------
        # Binary operation
        # --------------------------------------------------------------

        elif isinstance(node, BinOp):

            left = self.gen_expr(node.left)
            right = self.gen_expr(node.right)

            return self.program.append(
                BinOpTriple(
                    node.op,
                    left,
                    right,
                    node.result_type
                )
            )

        # --------------------------------------------------------------
        # Relational operation
        # --------------------------------------------------------------

        elif isinstance(node, RelOp):
            return self.gen_relop(node)

        # --------------------------------------------------------------
        # Cast
        # --------------------------------------------------------------

        elif isinstance(node, Cast):
            return self.gen_cast(node)

        # --------------------------------------------------------------
        # Ternary
        # --------------------------------------------------------------

        elif isinstance(node, Ternary):
            return self.gen_ternary(node)

        else:
            raise ValueError(
                f"unexpected expr node type: {type(node)}"
            )

    # ------------------------------------------------------------------
    # RelOp
    # ------------------------------------------------------------------

    def gen_relop(self, node):
        """
        Generate a RelOpTriple.

        A relational expression always produces an INT result (0 or 1),
        but the operands may be INT, CHAR, or DOUBLE.

        Week 6's type checker has already inserted any required Cast
        nodes, so node.left and node.right have the same promoted
        result_type.

        IMPORTANT:
            Use node.left.result_type as the operand_type.

            Do NOT use node.result_type because that describes the
            logical result of the comparison, which is always INT.
        """

        left = self.gen_expr(node.left)

        right = self.gen_expr(node.right)

        return self.program.append(
            RelOpTriple(
                node.op,
                left,
                right,
                node.left.result_type
            )
        )

    # ------------------------------------------------------------------
    # Cast
    # ------------------------------------------------------------------

    def gen_cast(self, node):
        """
        Generate a CastTriple.

        source_type:
            Type of the expression being converted.

        target_type:
            Type the expression should become.
        """

        arg = self.gen_expr(node.expr)

        return self.program.append(
            CastTriple(
                node.expr.result_type,
                node.target_type,
                arg
            )
        )

    # ------------------------------------------------------------------
    # Ternary
    # ------------------------------------------------------------------

    def gen_ternary(self, node):
        """
        Generate one SelectTriple for:

            condition ? then_expr : else_expr

        No branches or labels are generated here.

        Branching is handled by tac_to_mips.py when the SelectTriple
        is translated to MIPS.
        """

        cond = self.gen_expr(node.cond)

        then_val = self.gen_expr(node.then_expr)

        else_val = self.gen_expr(node.else_expr)

        return self.program.append(
            SelectTriple(
                cond,
                node.cond.result_type,
                then_val,
                else_val,
                node.result_type
            )
        )


# ======================================================================
# Convenience wrapper
# ======================================================================

def generate_for_function(function):
    """
    Generate TAC for one function using a fresh TACGenerator.
    """

    return TACGenerator().generate(function)

