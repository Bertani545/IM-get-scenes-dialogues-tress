from controlFlow import RegisterState,  copy_register_state
from decodeFunction import DecodedInstruction

MASK32 = 0xFFFFFFFF
MASK64 = 0xFFFFFFFFFFFFFFFF
def sign_extend_32(value: int) -> int:
    value &= MASK32

    if value & 0x80000000:
        return value - 0x100000000

    return value

def unsigned_32(value: int) -> int:
    return value & MASK32

def write_low32(
    registers: dict[str, RegisterState],
    register: str,
    value: int,
    insn: DecodedInstruction,
):
    if register == "zero":
        return

    state = registers[register]

    state.value = (
        state.value & 0xFFFFFFFF00000000
    ) | (value & MASK32)

    state.low_instruction = insn

def write_64(
    registers: dict[str, RegisterState],
    register: str,
    value: int,
    insn: DecodedInstruction,
):
    if register == "zero":
        return

    state = registers[register]

    state.value = value & MASK64

    state.low_instruction = insn
    state.high_instruction = insn

def write_unknown_low32(
    registers: dict[str, RegisterState],
    register: str,
    insn: DecodedInstruction,
):
    if register == "zero":
        return

    state = registers[register]

    state.value = None
    state.low_instruction = insn

def write_64_unknown(
    registers: dict[str, RegisterState],
    register: str,
    insn: DecodedInstruction,
):
    if register == "zero":
        return

    state = registers[register]

    state.value = None
    state.low_instruction = insn
    state.high_instruction = insn

def execute_instruction(
        registers: dict[str, RegisterState],
        insn: DecodedInstruction,
    ) -> dict[str, RegisterState]:

        new_registers = copy_register_state(registers)

        if insn.mnemonic == "move":

            dest = insn.writes_register
            source = insn.source_registers[0]

            write_low32(
                new_registers,
                dest,
                new_registers[source].value,
                insn,
            )

            return new_registers
        
        if insn.mnemonic == "lui":

            dest = insn.writes_register

            if dest is None or insn.immediate is None:
                print("Invalid lui")
                print(insn)
                return new_registers

            value = (
                insn.immediate << 16
            ) & MASK32

            write_low32(
                new_registers,
                dest,
                value,
                insn,
            )

            return new_registers



        if insn.mnemonic == "addiu":

            dest = insn.writes_register

            if dest is None or insn.immediate is None:
                print("Invalid addiu")
                print(insn)
                return new_registers

            sources = insn.source_registers

            if len(sources) != 1:
                print("Invalid addiu")
                print(insn)
                return new_registers

            source = sources[0]

            source_value = new_registers[source].value

            result = (
                source_value +
                insn.immediate
            ) & MASK32

            write_low32(
                new_registers,
                dest,
                result,
                insn,
            )

            return new_registers


        if insn.mnemonic == "addu":

            dest = insn.writes_register

            if dest is None:
                print("Invalid addu")
                print(insn)
                return new_registers

            sources = insn.source_registers

            if len(sources) != 2:
                print("Invalid addu")
                print(insn)
                return new_registers

            lhs = new_registers[sources[0]].value
            rhs = new_registers[sources[1]].value

            result = (
                lhs + rhs
            ) & MASK32

            write_low32(
                new_registers,
                dest,
                result,
                insn,
            )

            return new_registers



        if insn.mnemonic == "sll":

            dest = insn.writes_register

            if dest is None or insn.immediate is None:
                print("Invalid sll")
                print(insn)
                return new_registers

            sources = insn.source_registers

            if len(sources) != 1:
                print("Invalid sll")
                print(insn)
                return new_registers

            source = new_registers[sources[0]].value

            result = (
                source << insn.immediate
            ) & MASK32

            write_low32(
                new_registers,
                dest,
                result,
                insn,
            )

            return new_registers



        if insn.mnemonic in {"and", "or", "xor"}:
            dest = insn.writes_register
            sources = insn.source_registers

            if dest is None or len(sources) != 2:
                return new_registers

            lhs = new_registers[sources[0]].value
            rhs = new_registers[sources[1]].value

            if lhs is None or rhs is None:
                write_low32(new_registers, dest, 0, insn)
                new_registers[dest].value = None
                return new_registers

            if insn.mnemonic == "and":
                result = lhs & rhs
            elif insn.mnemonic == "or":
                result = lhs | rhs
            else:
                result = lhs ^ rhs

            write_low32(
                new_registers,
                dest,
                result,
                insn,
            )

            return new_registers

        if insn.mnemonic in {"andi", "ori", "xori"}:
            dest = insn.writes_register

            if dest is None or insn.immediate is None:
                return new_registers

            sources = insn.source_registers

            if len(sources) != 1:
                return new_registers

            source = new_registers[sources[0]].value

            if source is None:
                write_low32(new_registers, dest, 0, insn)
                new_registers[dest].value = None
                return new_registers

            imm = insn.immediate & 0xFFFF

            if insn.mnemonic == "andi":
                result = source & imm
            elif insn.mnemonic == "ori":
                result = source | imm
            else:
                result = source ^ imm

            write_low32(
                new_registers,
                dest,
                result,
                insn,
            )

            return new_registers

        if insn.mnemonic in {"subu", "sub"}:
            dest = insn.writes_register
            sources = insn.source_registers

            if dest is None or len(sources) != 2:
                return new_registers

            lhs = new_registers[sources[0]].value
            rhs = new_registers[sources[1]].value

            if lhs is None or rhs is None:
                write_low32(new_registers, dest, 0, insn)
                new_registers[dest].value = None
                return new_registers

            result = (lhs - rhs) & MASK32

            write_low32(
                new_registers,
                dest,
                result,
                insn,
            )

            return new_registers

        if insn.mnemonic in {"srl", "sra"}:
            dest = insn.writes_register
            sources = insn.source_registers

            if dest is None or len(sources) != 1:
                return new_registers

            source = new_registers[sources[0]].value

            if source is None or insn.immediate is None:
                write_low32(new_registers, dest, 0, insn)
                new_registers[dest].value = None
                return new_registers

            value = source & MASK32
            shift = insn.immediate

            if insn.mnemonic == "srl":
                result = value >> shift
            else:
                # Sign-extend the 32-bit operand before arithmetic shift.
                result = sign_extend_32(value) >> shift

            write_low32(
                new_registers,
                dest,
                result,
                insn,
            )

            return new_registers

        if insn.mnemonic == "lw":

            dest = insn.writes_register

            if dest is None:
                return new_registers

            write_unknown_low32(
                new_registers,
                dest,
                insn,
            )

            return new_registers

        if insn.mnemonic in {
            "lw",
            "lwu",
            "lh",
            "lhu",
            "lb",
            "lbu",
        }:

            dest = insn.writes_register

            if dest is None:
                return new_registers

            write_unknown_low32(
                new_registers,
                dest,
                insn,
            )

            return new_registers

        if insn.mnemonic == "ld":

            dest = insn.writes_register

            if dest is None:
                return new_registers

            if dest != "zero":
                state = new_registers[dest]

                state.value = None
                state.low_instruction = insn
                state.high_instruction = insn

            return new_registers

        if insn.mnemonic == "daddiu":

            dest = insn.writes_register

            if dest is None or insn.immediate is None:
                return new_registers

            sources = insn.source_registers

            if len(sources) != 1:
                return new_registers

            source_value = new_registers[sources[0]].value

            if source_value is None:
                write_64_unknown(
                    new_registers,
                    dest,
                    insn,
                )
                return new_registers

            result = (
                source_value + insn.immediate
            ) & MASK64

            write_64(
                new_registers,
                dest,
                result,
                insn,
            )

            return new_registers

        '''
       	raise NotImplementedError(
       	    f"Instruction not implemented: "
       	    f"{insn.address:08X}: "
       	    f"{insn.mnemonic} {insn.op_str}"
       	)
       	'''
        return new_registers