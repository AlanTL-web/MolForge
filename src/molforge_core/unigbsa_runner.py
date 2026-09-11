"""Process-local adapter for independent Uni-GBSA equilibration lengths."""
from contextlib import contextmanager
from functools import wraps
import inspect
import sys


@contextmanager
def equilibration_steps(engine, nvt_steps, npt_steps):
    originals = {}
    try:
        for name, count in (("gmx_nvt", nvt_steps), ("gmx_npt", npt_steps)):
            if type(count) is not int or count < 1:
                raise ValueError("Equilibration steps must be positive integers.")
            original = getattr(engine, name)
            signature = inspect.signature(original)
            if "nsteps" not in signature.parameters:
                raise RuntimeError(f"Unsupported Uni-GBSA API: {name} has no nsteps parameter")
            originals[name] = original

            def wrap(method, sig, steps):
                @wraps(method)
                def invoke(*args, **kwargs):
                    bound = sig.bind(*args, **kwargs)
                    bound.arguments["nsteps"] = steps
                    print(f"MolForge {method.__name__}: {steps} steps", flush=True)
                    return method(*bound.args, **bound.kwargs)
                return invoke

            setattr(engine, name, wrap(original, signature, count))
        yield
    finally:
        for name, original in originals.items():
            setattr(engine, name, original)


def main():
    from unigbsa.simulation.mdrun import GMXEngine
    from unigbsa.pipeline import main as pipeline_main
    nvt, npt = map(int, sys.argv[1:3])
    sys.argv = sys.argv[3:]
    with equilibration_steps(GMXEngine, nvt, npt):
        return pipeline_main()


if __name__ == "__main__":
    sys.exit(main())
