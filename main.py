"""A Drafter website for exploring common calculus and sequence problems.

Functions are entered with Python-style syntax, such as ``x**2`` or
``sin(x)``. Expressions are parsed and evaluated from a small allowlist
instead of being passed to ``eval``. Derivatives and integrals use
numerical approximations, so displayed results are approximate.
"""

import ast
import math
import operator
from collections.abc import Callable
from dataclasses import dataclass, field

from drafter import (
    Button,
    Div,
    Header,
    HorizontalRule,
    Link,
    Page,
    SelectBox,
    TextBox,
    hide_debug_information,
    route,
    set_site_information,
    set_website_framed,
    set_website_title,
    start_server,
)


PAGE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { color-scheme: dark; --ink: #edf2ff; --muted: #9daac5; --line: #293650;
  --panel: #111b2e; --bg: #09111f; --cyan: #66e3df; --violet: #9a8cff; }
* { box-sizing: border-box; }
body { background: radial-gradient(ellipse at 75% -15%, #202957 0, transparent 42%),
  var(--bg); color: var(--ink); font-family: 'DM Sans', sans-serif;
  max-width: 920px; margin: 0 auto; padding: 28px 24px 64px; line-height: 1.65; }
.drafter-body-- { color: var(--ink); }
h1, h2, h3 { color: var(--ink); font-family: 'Space Grotesk', sans-serif;
  letter-spacing: -.035em; }
h1 { font-size: clamp(2.5rem, 8vw, 5rem); line-height: 1.05; margin: 25px 0 16px; }
h2 { font-size: 2rem; margin-top: 20px; }
p { color: var(--muted); max-width: 70ch; }
a, button { color: var(--bg); background: var(--cyan); border: 0; border-radius: 9px;
  display: inline-block; font: 700 1rem 'DM Sans', sans-serif; margin: 8px 8px 8px 0;
  padding: 12px 18px; text-decoration: none; cursor: pointer; }
a:hover, button:hover { filter: brightness(1.12); transform: translateY(-1px); }
input, select { background: #0c1628; border: 1px solid var(--line); border-radius: 8px;
  color: var(--ink); display: block; font: 1rem 'DM Mono', monospace;
  margin: 6px 0 20px; max-width: 100%; padding: 12px 14px; width: min(520px, 100%); }
label { color: var(--ink); display: block; font-weight: 600; margin-top: 18px; }
hr { border: 0; border-top: 1px solid var(--line); margin: 28px 0; }
.eyebrow { color: var(--cyan); font: 500 .8rem 'DM Mono', monospace;
  letter-spacing: .14em; text-transform: uppercase; }
.card { background: linear-gradient(145deg, #121d32, #0d1729); border: 1px solid var(--line);
  border-radius: 14px; margin: 12px 0; padding: 20px 24px; }
.grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); }
.formula { color: var(--cyan); font: 1rem 'DM Mono', monospace; overflow-wrap: anywhere; }
.answer { color: var(--cyan); font: 600 clamp(2rem, 7vw, 3.5rem) 'DM Mono', monospace; }
.math-preview { background: #0c1628; border: 1px solid var(--line);
  border-radius: 8px; margin: 6px 0 20px; min-height: 54px; overflow-x: auto;
  padding: 14px; }
.math-preview mjx-container { color: var(--ink); margin: 0 !important; }
.muted { color: var(--muted); }
.secondary { background: var(--violet); }
"""

# MathJax only formats the live preview. The submitted expression remains in
# the app's existing restricted Python-style syntax and evaluator.
MATHJAX_PREVIEW_JS = r"""
(function () {
  const input = document.querySelector('input[name="expression"]');
  const preview = document.getElementById("math-preview");
  if (!input || !preview) {
    return;
  }

  function expressionToTex(source) {
    let tex = source.replace(/[\\{}$%&#_]/g, function (character) {
      const replacements = {
        "\\": "\\backslash ",
        "{": "\\{",
        "}": "\\}",
        "$": "\\$",
        "%": "\\bmod ",
        "&": "\\&",
        "#": "\\#",
        "_": "\\_"
      };
      return replacements[character];
    });

    return tex
      .replace(/\*\*/g, "^")
      .replace(/\bsqrt\s*\(([^()]*)\)/g, "\\sqrt{$1}")
      .replace(/\^(\([^()]*\)|[A-Za-z0-9.]+)/g, "^{$1}")
      .replace(/\(/g, "\\left(")
      .replace(/\)/g, "\\right)")
      .replace(/\b(sin|cos|tan|asin|acos|atan|log10|log|exp)\s*\\left\(/g,
        "\\$1\\left(")
      .replace(/\babs\s*\\left\(/g, "\\operatorname{abs}\\left(")
      .replace(/\bpi\b/g, "\\pi")
      .replace(/\be\b/g, "\\mathrm{e}")
      .replace(/\*/g, "\\cdot ")
      .replace(/\//g, "\\,/\\,");
  }

  function renderPreview() {
    const mathJax = window.MathJax;
    if (!mathJax || !mathJax.typesetPromise) {
      return;
    }

    mathJax.typesetClear([preview]);
    const expression = input.value.trim();
    if (!expression) {
      preview.textContent = "Enter a function to see its formatted preview.";
      return;
    }

    preview.textContent = "\\( f(x) = " + expressionToTex(expression) + " \\)";
    mathJax.typesetPromise([preview]).catch(function () {
      preview.textContent = "Preview unavailable for this expression.";
    });
  }

  function loadMathJax() {
    if (window.MathJax && window.MathJax.typesetPromise) {
      return window.MathJax.startup.promise;
    }
    if (!window.__calculusMathJaxPromise) {
      window.MathJax = window.MathJax || {
        tex: { inlineMath: [["\\(", "\\)"]] },
        startup: { typeset: false }
      };
      window.__calculusMathJaxPromise = new Promise(function (resolve, reject) {
        const script = document.createElement("script");
        script.src = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js";
        script.async = true;
        script.onload = function () {
          window.MathJax.startup.promise.then(function () {
            resolve(window.MathJax);
          }, reject);
        };
        script.onerror = function () {
          reject(new Error("MathJax could not be loaded."));
        };
        document.head.appendChild(script);
      });
    }
    return window.__calculusMathJaxPromise;
  }

  let updateTimer;
  input.addEventListener("input", function () {
    window.clearTimeout(updateTimer);
    updateTimer = window.setTimeout(renderPreview, 120);
  });

  preview.textContent = "Loading formatted preview...";
  loadMathJax().then(renderPreview).catch(function () {
    preview.textContent = "MathJax could not load. Your function is still usable.";
  });
})();
"""

ALLOWED_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
ALLOWED_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
ALLOWED_FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
}
MAX_EXPRESSION_LENGTH = 120
INTEGRATION_STEPS = 1000


@dataclass
class CalculationRecord:
    """One completed problem retained in this visitor's session history."""

    problem_type: str
    expression: str
    answer: str
    explanation: str


@dataclass
class State:
    """Mutable values maintained between pages for one visitor."""

    history: list[CalculationRecord] = field(default_factory=list)
    selected_calculator: str = "derivative"
    last_answer: str = ""
    last_explanation: str = ""
    calculations_made: int = 0
    last_problem: str = ""


def evaluate_expression(expression: str, x_value: float) -> float:
    """Evaluate a math expression using only supported arithmetic and functions."""
    if not expression or len(expression) > MAX_EXPRESSION_LENGTH:
        raise ValueError("Enter a non-empty expression no longer than 120 characters.")
    normalized = expression.replace("^", "**")
    try:
        parsed = ast.parse(normalized, mode="eval")
        result = _evaluate_node(parsed.body, x_value)
    except (SyntaxError, OverflowError, TypeError) as error:
        raise ValueError("Use a supported expression such as x**2 + sin(x).") from error
    if not math.isfinite(result):
        raise ValueError("The expression did not produce a finite real number.")
    return result


def _evaluate_node(node: ast.AST, x_value: float) -> float:
    """Evaluate one syntax-tree node; unsupported Python syntax is rejected."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name):
        constants = {"x": x_value, "pi": math.pi, "e": math.e}
        if node.id in constants:
            return constants[node.id]
        raise ValueError("Use x, pi, e, or a supported math function.")
    if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_BINARY_OPERATORS:
        left = _evaluate_node(node.left, x_value)
        right = _evaluate_node(node.right, x_value)
        try:
            return ALLOWED_BINARY_OPERATORS[type(node.op)](left, right)
        except (OverflowError, ZeroDivisionError, ValueError) as error:
            raise ValueError("That expression is undefined for the requested value.") from error
    if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_UNARY_OPERATORS:
        return ALLOWED_UNARY_OPERATORS[type(node.op)](_evaluate_node(node.operand, x_value))
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in ALLOWED_FUNCTIONS
        and len(node.args) == 1
        and not node.keywords
    ):
        try:
            return ALLOWED_FUNCTIONS[node.func.id](
                _evaluate_node(node.args[0], x_value)
            )
        except (OverflowError, ValueError) as error:
            raise ValueError("That function is undefined for the requested value.") from error
    raise ValueError("Use arithmetic, x, pi, e, and a supported one-input math function.")


def derivative_at(expression: str, x_value: float) -> float:
    """Approximate the derivative using a centered difference."""
    step = 1e-5 * max(1.0, abs(x_value))
    return (
        evaluate_expression(expression, x_value + step)
        - evaluate_expression(expression, x_value - step)
    ) / (2 * step)


def simpson_integral(expression: str, lower: float, upper: float) -> float:
    """Approximate a definite integral with composite Simpson's rule."""
    if lower == upper:
        return 0.0
    direction = 1.0
    if upper < lower:
        lower, upper = upper, lower
        direction = -1.0
    step = (upper - lower) / INTEGRATION_STEPS
    total = evaluate_expression(expression, lower) + evaluate_expression(
        expression, upper
    )
    for index in range(1, INTEGRATION_STEPS):
        multiplier = 4 if index % 2 else 2
        total += multiplier * evaluate_expression(
            expression, lower + index * step
        )
    return direction * total * step / 3


def sequence_sum(first_term: float, common_value: float, terms: int, kind: str) -> float:
    """Return the sum of an arithmetic or geometric sequence."""
    if terms < 1:
        raise ValueError("The number of terms must be at least 1.")
    if terms > 100000:
        raise ValueError("Please enter 100,000 terms or fewer.")
    if kind == "Arithmetic":
        return terms * (2 * first_term + (terms - 1) * common_value) / 2
    if kind == "Geometric":
        if common_value == 1:
            return first_term * terms
        return first_term * (1 - common_value**terms) / (1 - common_value)
    raise ValueError("Choose either an arithmetic or geometric sequence.")


def arc_length(expression: str, lower: float, upper: float) -> float:
    """Approximate arc length by integrating sqrt(1 + (dy/dx)^2)."""
    if lower == upper:
        return 0.0
    return simpson_values(
        lambda value: math.sqrt(1 + derivative_at(expression, value) ** 2),
        min(lower, upper),
        max(lower, upper),
    )


def simpson_values(
    function: Callable[[float], float], lower: float, upper: float
) -> float:
    """Integrate a numeric function using composite Simpson's rule."""
    step = (upper - lower) / INTEGRATION_STEPS
    total = function(lower) + function(upper)
    for index in range(1, INTEGRATION_STEPS):
        total += (4 if index % 2 else 2) * function(lower + index * step)
    return total * step / 3


def _format_number(value: float) -> str:
    """Format a result clearly without trailing zeroes."""
    return f"{value:.10g}"


def _save_result(
    state: State,
    problem_type: str,
    route_name: str,
    expression: str,
    answer: float,
    explanation: str,
) -> None:
    """Update the session's latest result and add it to the calculation history."""
    state.last_answer = _format_number(answer)
    state.last_explanation = explanation
    state.last_problem = expression
    state.selected_calculator = route_name
    state.calculations_made += 1
    state.history.append(
        CalculationRecord(
            problem_type=problem_type,
            expression=expression,
            answer=state.last_answer,
            explanation=explanation,
        )
    )


def _result_page(state: State) -> Page:
    """Build the shared result page from the latest session result."""
    return Page(
        state,
        [
            Link("← All calculators", calculators),
            Header("Your result", 1),
            Div(
                Header(state.last_problem, 3),
                Div(state.last_answer, class_="answer"),
                Header("How it was calculated", 3),
                state.last_explanation,
                class_="card",
            ),
            Link("Try another problem", state.selected_calculator),
            Link("View history", history),
        ],
        css=PAGE_CSS,
    )


def _parse_number(value: str, label: str) -> float:
    """Parse a finite numeric input or provide a useful validation message."""
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Enter a valid number for {label}.") from error
    if not math.isfinite(number):
        raise ValueError(f"{label.capitalize()} must be a finite number.")
    return number


def _calculator_page(
    state: State,
    title: str,
    fields: list[object],
    submit_route: Callable[..., Page],
    show_math_preview: bool = False,
) -> Page:
    """Render a calculator form with consistent navigation and styling."""
    return Page(
        state,
        [
            Link("← All calculators", calculators),
            Header(title, 1),
            Div(*fields, Button("Calculate", submit_route), class_="card"),
            Link("Calculation history", history),
        ],
        css=PAGE_CSS,
        js=MATHJAX_PREVIEW_JS if show_math_preview else None,
    )


@route
def home(state: State) -> Page:
    """Show the site's welcome page."""
    return Page(
        state,
        [
            Div("CALCULUS, MADE CLEAR", class_="eyebrow"),
            Header("Math, meet\nmomentum.", 1),
            Div(
                "A friendly workspace for exploring derivatives, integrals, "
                "sequence sums, and curve lengths.",
                class_="card",
            ),
            Link("Get started →", calculators),
            HorizontalRule(),
            Div(
                "Enter expressions like x**2, sin(x), or sqrt(x). "
                "Numerical answers are approximations.",
                class_="muted",
            ),
        ],
        css=PAGE_CSS,
    )


@route("index")
def index(state: State) -> Page:
    """Serve the welcome page at Drafter's root URL."""
    return home(state)


@route
def calculators(state: State) -> Page:
    """List the available calculators."""
    return Page(
        state,
        [
            Div("PICK A TOOL", class_="eyebrow"),
            Header("Calculator studio", 1),
            Div(
                Link("Derivative →", derivative),
                Link("Definite integral →", integral),
                Link("Sequence sum →", sequence),
                Link("Arc length →", arc_length_page),
                class_="grid",
            ),
            Link("Calculation history", history),
            Link("Home", home),
        ],
        css=PAGE_CSS,
    )


@route
def derivative(state: State) -> Page:
    """Show the derivative calculator form."""
    state.selected_calculator = "derivative"
    return _calculator_page(
        state,
        "Derivative",
        [
            Header("Estimate the slope at a point.", 3),
            "Supported functions: sin, cos, tan, asin, acos, atan, sqrt, log, "
            "log10, exp, and abs.",
            "Function f(x)",
            TextBox("expression", "x**2"),
            Div(
                "Loading formatted preview...",
                id="math-preview",
                class_="math-preview",
            ),
            "Evaluate at x",
            TextBox("x_value", "3", kind="number", step="any"),
        ],
        calculate_derivative,
        show_math_preview=True,
    )


@route
def integral(state: State) -> Page:
    """Show the definite-integral calculator form."""
    state.selected_calculator = "integral"
    return _calculator_page(
        state,
        "Definite integral",
        [
            Header("Estimate the signed area under a curve.", 3),
            "Function f(x)",
            TextBox("expression", "x**2"),
            Div(
                "Loading formatted preview...",
                id="math-preview",
                class_="math-preview",
            ),
            "Lower bound",
            TextBox("lower", "0", kind="number", step="any"),
            "Upper bound",
            TextBox("upper", "3", kind="number", step="any"),
        ],
        calculate_integral,
        show_math_preview=True,
    )


@route
def sequence(state: State) -> Page:
    """Show the arithmetic and geometric sequence calculator form."""
    state.selected_calculator = "sequence"
    return _calculator_page(
        state,
        "Sequence sum",
        [
            Header("Add the first n terms.", 3),
            "Sequence type",
            SelectBox("kind", ["Arithmetic", "Geometric"], "Arithmetic"),
            "First term",
            TextBox("first_term", "2", kind="number", step="any"),
            "Common difference or ratio",
            TextBox("common_value", "3", kind="number", step="any"),
            "Number of terms",
            TextBox("terms", "5", kind="number", min="1", step="1"),
        ],
        calculate_sequence,
    )


@route
def arc_length_page(state: State) -> Page:
    """Show the arc-length calculator form."""
    state.selected_calculator = "arc_length_page"
    return _calculator_page(
        state,
        "Arc length",
        [
            Header("Estimate the length of a curve segment.", 3),
            "Function y = f(x)",
            TextBox("expression", "x**2"),
            Div(
                "Loading formatted preview...",
                id="math-preview",
                class_="math-preview",
            ),
            "Starting x-value",
            TextBox("lower", "0", kind="number", step="any"),
            "Ending x-value",
            TextBox("upper", "1", kind="number", step="any"),
        ],
        calculate_arc_length,
        show_math_preview=True,
    )


@route
def calculate_derivative(
    state: State, expression: str = "x**2", x_value: str = "0"
) -> Page:
    """Calculate a numerical derivative and show its explanation."""
    try:
        point = _parse_number(x_value, "x-value")
        answer = derivative_at(expression, point)
    except ValueError as error:
        return Page(
            state,
            [Header("Check your input", 1), str(error), Link("Try again", derivative)],
            css=PAGE_CSS,
        )
    explanation = (
        f"Centered difference: [f(x + h) - f(x - h)] / (2h), "
        f"with x = {point:g} and h = 0.00001 × max(1, |x|)."
    )
    _save_result(
        state,
        "Derivative",
        "derivative",
        f"f(x) = {expression}; x = {point:g}",
        answer,
        explanation,
    )
    return _result_page(state)


@route
def calculate_integral(
    state: State, expression: str = "x**2", lower: str = "0", upper: str = "1"
) -> Page:
    """Calculate a definite integral and show its approximation method."""
    try:
        start = _parse_number(lower, "lower bound")
        end = _parse_number(upper, "upper bound")
        answer = simpson_integral(expression, start, end)
    except ValueError as error:
        return Page(
            state,
            [Header("Check your input", 1), str(error), Link("Try again", integral)],
            css=PAGE_CSS,
        )
    explanation = (
        f"Composite Simpson's rule estimates the signed area from "
        f"x = {start:g} to x = {end:g} using {INTEGRATION_STEPS} subintervals."
    )
    _save_result(
        state,
        "Integral",
        "integral",
        f"∫ {expression} dx from {start:g} to {end:g}",
        answer,
        explanation,
    )
    return _result_page(state)


@route
def calculate_sequence(
    state: State,
    kind: str = "Arithmetic",
    first_term: str = "1",
    common_value: str = "1",
    terms: str = "1",
) -> Page:
    """Calculate the sum of the selected arithmetic or geometric sequence."""
    try:
        first = _parse_number(first_term, "first term")
        common = _parse_number(common_value, "common difference or ratio")
        count = int(terms)
        if str(count) != terms.strip():
            raise ValueError("The number of terms must be a whole number.")
        answer = sequence_sum(first, common, count, kind)
    except (ValueError, OverflowError) as error:
        return Page(
            state,
            [
                Header("Check your input", 1),
                str(error),
                Link("Try again", sequence),
            ],
            css=PAGE_CSS,
        )
    symbol = "d" if kind == "Arithmetic" else "r"
    explanation = (
        f"{kind} series with first term {first:g}, {symbol} = {common:g}, "
        f"and n = {count}. The standard finite-series sum formula was used."
    )
    _save_result(
        state,
        "Sequence sum",
        "sequence",
        f"{kind}: a₁ = {first:g}, {symbol} = {common:g}, n = {count}",
        answer,
        explanation,
    )
    return _result_page(state)


@route
def calculate_arc_length(
    state: State, expression: str = "x**2", lower: str = "0", upper: str = "1"
) -> Page:
    """Calculate a numerical arc length and show its approximation method."""
    try:
        start = _parse_number(lower, "starting x-value")
        end = _parse_number(upper, "ending x-value")
        answer = arc_length(expression, start, end)
    except (ValueError, OverflowError) as error:
        return Page(
            state,
            [
                Header("Check your input", 1),
                str(error),
                Link("Try again", arc_length_page),
            ],
            css=PAGE_CSS,
        )
    explanation = (
        "Arc length is estimated by integrating sqrt(1 + (f'(x))²); "
        f"centered differences and Simpson's rule use {INTEGRATION_STEPS} "
        "subintervals."
    )
    _save_result(
        state,
        "Arc length",
        "arc_length_page",
        f"y = {expression} from x = {start:g} to {end:g}",
        answer,
        explanation,
    )
    return _result_page(state)


@route
def results(state: State) -> Page:
    """Display the most recently calculated result."""
    if state.last_answer:
        return _result_page(state)
    return Page(
        state,
        [
            Header("No result yet", 1),
            "Choose a calculator and solve a problem to see it here.",
            Link("Open calculators", calculators),
        ],
        css=PAGE_CSS,
    )


@route
def history(state: State) -> Page:
    """Show saved problems and answers from this visitor's session."""
    entries = []
    for record in reversed(state.history):
        entries.append(
            Div(
                Div(record.problem_type.upper(), class_="eyebrow"),
                Header(record.expression, 3),
                Div(record.answer, class_="formula"),
                record.explanation,
                class_="card",
            )
        )
    if not entries:
        entries = [Div("Your solved problems will appear here.", class_="card")]
    return Page(
        state,
        [
            Header("Calculation history", 1),
            Div(f"{state.calculations_made} problem(s) solved", class_="muted"),
            *entries,
            Link("Back to calculators", calculators),
            Link("Home", home),
        ],
        css=PAGE_CSS,
    )


if __name__ == "__main__":
    set_website_title("Calculus Studio")
    set_site_information(
        author="Python Project Calculus Site",
        description=(
            "Explore derivatives, definite integrals, sequence sums, "
            "and arc lengths."
        ),
        sources="Drafter library and MathJax.",
        planning=[],
        links=[
            "https://github.com/paintedblacknails/"
            "Python-Project-Calculus-Site"
        ],
    )
    hide_debug_information()
    set_website_framed(False)
    start_server(initial_state=State(), site_title="Calculus Studio")
