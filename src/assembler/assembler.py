import argparse
import sys
from dataclasses import dataclass
from typing import List, Optional

import yaml


# Variant 23 opcodes (A fields)
OPCODES = {
    "LOAD_CONST": 14,   # A=14, 2 bytes (B is const)
    "READ_MEM": 38,     # A=38, 1 byte
    "WRITE_MEM": 27,    # A=27, 1 byte
    "LE": 12,           # A=12, 1 byte
}


@dataclass
class IRInstr:
    op: str
    A: int
    B: Optional[int] = None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="UVM Assembler (YAML) — Stage 1")
    p.add_argument("--src", required=True, help="Path to YAML source")
    p.add_argument("--out", required=True, help="Path to output binary (stage 1 creates empty file)")
    p.add_argument("--test", action="store_true", help="Print IR (fields and values)")
    return p.parse_args()


def load_yaml(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: source file not found: {path}")
    except yaml.YAMLError as e:
        raise SystemExit(f"ERROR: YAML parse error: {e}")

    if not isinstance(data, list):
        raise SystemExit("ERROR: YAML top-level must be a list of instructions")

    return data


def build_ir(program):
    ir = []

    for i, instr in enumerate(program):
        if not isinstance(instr, dict):
            raise SystemExit(f"ERROR: instruction #{i} must be a YAML mapping/object")

        op = instr.get("op")
        if not isinstance(op, str):
            raise SystemExit(f"ERROR: instruction #{i} missing string field 'op'")

        op = op.strip()
        if op not in OPCODES:
            raise SystemExit(f"ERROR: instruction #{i} unknown op '{op}'")

        A = OPCODES[op]

        if op == "LOAD_CONST":
            if "value" not in instr:
                raise SystemExit(f"ERROR: instruction #{i} LOAD_CONST requires field 'value'")
            try:
                B = int(instr["value"])
            except Exception:
                raise SystemExit(f"ERROR: instruction #{i} LOAD_CONST 'value' must be an integer")
            ir.append(IRInstr(op=op, A=A, B=B))
        else:
            ir.append(IRInstr(op=op, A=A))

    return ir


def print_ir(ir):
    for idx, ins in enumerate(ir):
        if ins.B is None:
            print(f"{idx}: op={ins.op} A={ins.A}")
        else:
            print(f"{idx}: op={ins.op} A={ins.A} B={ins.B}")


def main() -> int:
    args = parse_args()
    program = load_yaml(args.src)
    ir = build_ir(program)

    if args.test:
        print_ir(ir)

    # Stage 1: create output file (binary content added in Stage 2)
    try:
        with open(args.out, "wb") as f:
            f.write(b"")
    except Exception as e:
        print(f"ERROR: cannot write output file: {e}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())