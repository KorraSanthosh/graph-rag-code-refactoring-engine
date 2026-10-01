import base64
import logging

logger = logging.getLogger(__name__)


class SemanticEquivalenceChecker:
    """
    Differential testing: verifies that the refactored function produces
    identical outputs to the original for a set of test inputs.

    This catches the case where the code runs successfully (passes Docker
    verification) but is semantically incorrect (changed behavior).
    """

    def check(
        self,
        original_code: str,
        refactored_code: str,
        func_name: str,
        test_inputs: list[tuple],
    ) -> tuple[bool, str]:
        """
        Args:
            original_code: Original Python source as a string
            refactored_code: Refactored Python source as a string
            func_name: Name of the function to test
            test_inputs: List of argument tuples, e.g. [(1, 2), (3, 4)]

        Returns:
            (success: bool, message: str)
        """
        try:
            orig_fn = self._load_function(original_code, func_name)
            new_fn = self._load_function(refactored_code, func_name)
        except Exception as e:
            logger.error(f"Could not load function '{func_name}': {e}")
            return False, f"Load error: {e}"

        failures: list[str] = []
        for inputs in test_inputs:
            try:
                orig_result = orig_fn(*inputs)
                new_result = new_fn(*inputs)
                if orig_result != new_result:
                    failures.append(
                        f"Input {inputs}: expected {orig_result!r}, got {new_result!r}"
                    )
            except Exception as e:
                failures.append(f"Input {inputs}: exception — {e}")

        if failures:
            msg = f"Semantic equivalence FAILED ({len(failures)}/{len(test_inputs)} cases):\n" + "\n".join(failures)
            logger.warning(msg)
            return False, msg

        msg = f"✅ Semantically equivalent on all {len(test_inputs)} test cases."
        logger.info(msg)
        return True, msg

    def _load_function(self, code: str, func_name: str):
        """Compiles code and extracts the target function from its namespace."""
        namespace: dict = {}
        exec(compile(code, "<equivalence_check>", "exec"), namespace)
        if func_name not in namespace:
            raise ValueError(f"Function '{func_name}' not found in code.")
        return namespace[func_name]

    def check_sandboxed(
        self, original_code: str, refactored_code: str, func_name: str, verifier
    ) -> tuple[bool, str]:
        """
        Differential test run *inside the sandbox* (so generated code never executes in
        the API process). Inputs are synthesized from the function's signature; only
        inputs the original function accepts are compared, including in-place mutation
        of arguments. Methods (`Class.method`) are skipped.
        """
        if "." in func_name:
            return True, "Equivalence check skipped (methods are not supported)."
        harness = _HARNESS.format(
            orig=base64.b64encode(original_code.encode()).decode(),
            new=base64.b64encode(refactored_code.encode()).decode(),
            name=func_name,
        )
        ok, log = verifier.verify_code(harness)
        log = log.strip()
        if ok:
            return True, log.splitlines()[-1] if log else "Equivalence check passed."
        return False, f"Behavior changed vs. original:\n{log}"


_HARNESS = r"""
import base64, copy, inspect, itertools, random

name = "{name}"


def load(src):
    ns = {{"__name__": "__equiv__"}}
    exec(compile(base64.b64decode(src).decode(), "<code>", "exec"), ns)
    return ns[name]


try:
    orig = load("{orig}")
except Exception as e:
    print("Original code could not be loaded (%s: %s); equivalence not checked." % (type(e).__name__, e))
    raise SystemExit(0)
new = load("{new}")
POOL = [0, 1, 2, 5, -1, 3.5, "abc", "", "Hello World", [1, 2, 3, 4, 5], [], {{"a": 1, "b": 2}}, None, True]

try:
    params = [
        p for p in inspect.signature(orig).parameters.values()
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.default is p.empty
    ]
except (TypeError, ValueError):
    params = []
n = len(params)
if n == 0:
    candidates = [()]
else:
    combos = list(itertools.product(POOL, repeat=min(n, 3))) if n <= 3 else []
    random.Random(0).shuffle(combos)
    candidates = combos[:300]


def call(fn, args):
    args = copy.deepcopy(args)
    try:
        return ("ok", fn(*args), args)
    except Exception as e:
        return ("err", type(e).__name__, args)


tested = 0
for args in candidates:
    expected = call(orig, args)
    if expected[0] == "err":
        continue
    actual = call(new, args)
    tested += 1
    try:
        same = expected == actual
    except Exception:
        same = False
    if not same:
        raise SystemExit("Input %r: expected %r, got %r" % (args, expected[1], actual[1]))
    if tested >= 20:
        break
print("Behavior verified on %d input(s)." % tested if tested else "No valid test inputs found; equivalence not checked.")
"""
