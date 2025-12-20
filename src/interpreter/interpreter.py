import argparse
import csv
import sys
from dataclasses import dataclass
from typing import List, Optional


# Variant 23 opcodes (A fields)
A_LOAD_CONST = 14  # 2 bytes: word = A | (B << 6)
A_READ_MEM = 38    # 1 byte
A_WRITE_MEM = 27   # 1 byte
A_LE = 12          # 1 byte (stage 4+)

@dataclass
class IRInstr:
    op: str
    A: int
    B: Optional[int] = None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="UVM Interpreter — Stage 3")
    p.add_argument("--bin", required=True, help="Path to machine code binary")
    p.add_argument("--dump", required=True, help="Path to CSV memory dump")
    p.add_argument("--range", required=True, help="Dump range as start:end (e.g. 0:300)")
    p.add_argument("--mem-size", type=int, default=1024, help="Data memory size (default 1024)")
    return p.parse_args()


def parse_range(r: str) -> tuple[int, int]:
    try:
        a, b = r.split(":")
        start = int(a)
        end = int(b)
    except Exception:
        raise SystemExit("ERROR: --range must be in format start:end, e.g. 0:300")

    if start < 0 or end < 0 or end < start:
        raise SystemExit("ERROR: invalid --range values")
    return start, end


def load_bin(path: str) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        raise SystemExit(f"ERROR: binary file not found: {path}")


def decode(code: bytes) -> List[IRInstr]:
    """
    Decode machine code bytes into IR instructions.

    Variant 23:
      - LOAD_CONST: 2 bytes (little-endian word), fields:
            A = word & 0x3F   (6 bits)
            B = word >> 6
        where A must be 14
      - READ_MEM:  1 byte 0x26
      - WRITE_MEM: 1 byte 0x1B
      - LE:        1 byte 0x0C (executed from stage 4)
    """
    ir: List[IRInstr] = []
    i = 0
    n = len(code)

    one_byte = {
        A_READ_MEM: "READ_MEM",
        A_WRITE_MEM: "WRITE_MEM",
        A_LE: "LE",
    }

    while i < n:
        b0 = code[i]

        # 1-byte commands are unambiguous
        if b0 in one_byte:
            op = one_byte[b0]
            ir.append(IRInstr(op=op, A=b0))
            i += 1
            continue

        # Otherwise, try to decode 2-byte LOAD_CONST word
        if i + 1 >= n:
            raise SystemExit(f"ERROR: truncated 2-byte instruction at offset {i}")

        b1 = code[i + 1]
        word = b0 | (b1 << 8)          # little-endian word
        A = word & 0x3F                # lower 6 bits
        B = word >> 6

        if A != A_LOAD_CONST:
            raise SystemExit(f"ERROR: unknown opcode word 0x{word:04X} (A={A}) at offset {i}")

        ir.append(IRInstr(op="LOAD_CONST", A=A_LOAD_CONST, B=B))
        i += 2

    return ir

class VM:
    def __init__(self, mem_size: int):
        self.code_memory: List[IRInstr] = []          # память команд (IR)
        self.data_memory: List[int] = [0] * mem_size  # память данных
        self.stack: List[int] = []                    # стек

    def push(self, v: int) -> None:
        self.stack.append(int(v))

    def pop(self) -> int:
        if not self.stack:
            raise RuntimeError("Stack underflow")
        return self.stack.pop()

    def exec_one(self, ins: IRInstr) -> None:
        if ins.op == "LOAD_CONST":
            self.push(ins.B)
            return

        if ins.op == "READ_MEM":
            addr = self.pop()
            if addr < 0 or addr >= len(self.data_memory):
                raise RuntimeError(f"READ_MEM: address out of range: {addr}")
            self.push(self.data_memory[addr])
            return

        if ins.op == "WRITE_MEM":
            # порядок стека (важно!):
            # ... [addr, value] -> mem[addr] = value
            value = self.pop()
            addr = self.pop()
            if addr < 0 or addr >= len(self.data_memory):
                raise RuntimeError(f"WRITE_MEM: address out of range: {addr}")
            self.data_memory[addr] = value
            return

        if ins.op == "LE":
            # На этапе 3 выполнение LE НЕ требуется.
            # Мы специально падаем, чтобы не было “тихих” ошибок.
            raise RuntimeError("LE is not implemented in stage 3 (will be stage 4)")

        raise RuntimeError(f"Unknown IR op: {ins.op}")

    def run(self, ir: List[IRInstr]) -> None:
        self.code_memory = ir[:]  # раздельная память команд
        for ins in self.code_memory:
            self.exec_one(ins)


def dump_memory_csv(path: str, mem: List[int], start: int, end: int) -> None:
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["address", "value"])
            for addr in range(start, end + 1):
                if 0 <= addr < len(mem):
                    w.writerow([addr, mem[addr]])
                else:
                    # если диапазон выходит за пределы — можно либо пропускать, либо писать пусто
                    w.writerow([addr, ""])
    except Exception as e:
        raise SystemExit(f"ERROR: cannot write dump CSV: {e}")


def main() -> int:
    args = parse_args()
    start, end = parse_range(args.range)

    code = load_bin(args.bin)
    ir = decode(code)

    vm = VM(mem_size=args.mem_size)

    try:
        vm.run(ir)
    except Exception as e:
        print(f"RUNTIME ERROR: {e}", file=sys.stderr)
        return 2

    dump_memory_csv(args.dump, vm.data_memory, start, end)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
