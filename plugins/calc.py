"""
plugins/calc.py  –  Phoenix Plugin
Safely evaluates a math expression.
Usage: /calc 2 + 2 * 10
"""

import ast, math, operator

COMMAND     = "calc"
DESCRIPTION = "Evaluate a math expression safely"
USAGE       = "/calc <expression>   e.g. /calc (12 * 3) / 4 + sqrt(16)"

# ── Safe eval ─────────────────────────────────────────────────────────────────
_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
    ast.USub, ast.UAdd,
)

_SAFE_FUNCS = {
    "sqrt": math.sqrt, "abs":  abs,    "round": round,
    "ceil": math.ceil, "floor": math.floor,
    "log":  math.log,  "log10": math.log10,
    "sin":  math.sin,  "cos":  math.cos, "tan": math.tan,
    "pi":   math.pi,   "e":    math.e,
}


def _safe_eval(expr: str) -> float:
    tree = ast.parse(expr.strip(), mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"Unsafe operation: {type(node).__name__}")
    return eval(  # noqa: S307 – guarded by AST walk above
        compile(tree, "<calc>", "eval"),
        {"__builtins__": {}},
        _SAFE_FUNCS,
    )


def run(args: str, session_id: str = None) -> str:
    if not args.strip():
        return "Usage: /calc <expression>  e.g. /calc 12 * (3 + 4)"
    try:
        result = _safe_eval(args)
        # Format: drop .0 for whole numbers
        if isinstance(result, float) and result.is_integer():
            return f"{args.strip()} = {int(result)}"
        return f"{args.strip()} = {result}"
    except ZeroDivisionError:
        return "⚠️  Division by zero."
    except Exception as e:
        return f"⚠️  Could not evaluate: {e}"
