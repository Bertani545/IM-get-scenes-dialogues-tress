from dataclasses import dataclass, field
from typing import Optional
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS64, CS_MODE_LITTLE_ENDIAN



@dataclass
class DecodedInstruction:
    address: int
    mnemonic: str
    op_str: str
    bytes: bytes
    kind: str
    
    writes_register: Optional[str] = None
    source_registers: list[str] = field(default_factory=list)
    immediate: Optional[int] = None
    jump_target: Optional[int] = None

    tracked: bool = False

    def __str__(self):
        return (
            f"{self.address:08X}: "
            f"{self.mnemonic:<8} {self.op_str:<25} "
            f"[{self.kind}] "
            f"immediate = {hex(self.immediate) if self.immediate is not None else None} "
            f"Tracked: {self.tracked}"
        )


class MIPSDecoder:
    def __init__(self):
        self.cs = Cs(
            CS_ARCH_MIPS,
            CS_MODE_MIPS64 | CS_MODE_LITTLE_ENDIAN
        )

        self.cs.detail = True

        # Don't stop decoding just because Capstone encounters
        # something it doesn't recognize.
        self.cs.skipdata = True

    def decode(
        self,
        func_bytes: bytes,
        base_va: int,
        interesting_jals: set[int]
    ) -> list[DecodedInstruction]:

        instructions = []

        for insn in self.cs.disasm(func_bytes, base_va):

            mnemonic = insn.mnemonic.lower()
            if mnemonic != ".byte":
                # ---------------------------------------------------------
                # 1. BRANCH / JUMP INSTRUCTIONS
                # ---------------------------------------------------------

                if self._is_branch_or_jump(mnemonic):

                    # Direct branch/jump target, when Capstone provides one.
                    jump_target = self._get_jump_target(insn)

                    # jal is special: only keep it if it targets one
                    # of the functions we are interested in.
                    if mnemonic == "jal":

                        is_insteresting = (
                            jump_target is not None 
                            and jump_target in interesting_jals
                        )

                        
                        instructions.append(
                            DecodedInstruction(
                                address=insn.address,
                                mnemonic=insn.mnemonic,
                                op_str=insn.op_str,
                                bytes=bytes(insn.bytes),
                                kind="jal",
                                jump_target=jump_target,
                                source_registers=self._get_source_registers(insn),
                                immediate=self._get_immediate(insn),
                                tracked = is_insteresting,
                            )
                        )

                        continue

                    # All other branches/jumps are kept.
                    kind = self._branch_kind(mnemonic)

                    instructions.append(
                        DecodedInstruction(
                            address=insn.address,
                            mnemonic=insn.mnemonic,
                            op_str=insn.op_str,
                            bytes=bytes(insn.bytes),
                            kind=kind,
                            jump_target=jump_target,
                            source_registers=self._get_source_registers(insn),
                            immediate=self._get_immediate(insn),
                            tracked = True,
                        )
                    )

                    continue

                # ---------------------------------------------------------
                # 2. INSTRUCTIONS THAT WRITE TO INTEGER REGISTERS
                # ---------------------------------------------------------

                written_register = self._get_written_register(insn)

                if written_register is not None:

                    instructions.append(
                        DecodedInstruction(
                            address=insn.address,
                            mnemonic=insn.mnemonic,
                            op_str=insn.op_str,
                            bytes=bytes(insn.bytes),
                            kind="register_write",
                            writes_register=written_register,
                            source_registers=self._get_source_registers(insn),
                            immediate=self._get_immediate(insn),
                            tracked = True,
                        )
                    )
                    continue


                # Default
                instructions.append(
                    DecodedInstruction(
                        address=insn.address,
                        mnemonic=insn.mnemonic,
                        op_str=insn.op_str,
                        bytes=bytes(insn.bytes),
                        kind="other",
                        tracked = False,
                    )
                )
            else:
                instructions.append(
                    DecodedInstruction(
                        address=insn.address,
                        mnemonic=insn.mnemonic,
                        op_str=insn.op_str,
                        bytes=bytes(insn.bytes),
                        kind="other",
                        tracked = False,
                    )
                )

        return instructions

    # -----------------------------------------------------------------
    # Branch / jump detection
    # -----------------------------------------------------------------

    def _is_branch_or_jump(self, mnemonic: str) -> bool:

        return mnemonic in {
            # Direct jumps
            "j",
            "jal",

            # Register jumps
            "jr",
            "jalr",

            # Equality branches
            "beq",
            "bne",

            # Zero branches
            "beqz",
            "bnez",

            # Signed branches
            "bltz",
            "bgez",
            "blez",
            "bgtz",

            # Link variants
            "bltzal",
            "bgezal",

            # Likely variants
            "beql",
            "bnel",
            "blezl",
            "bgtzl",
            "bltzl",
            "bgezl",
            "bltzall",
            "bgezall",

            # MIPS pseudo-branches
            "b",
        }

    def _branch_kind(self, mnemonic: str) -> str:

        if mnemonic == "j" or mnemonic == "b":
            return "goto"

        if mnemonic in {"jr", "jalr"}:
            return "indirect_branch"

        return "branch"

    def _get_immediate(self, insn) -> Optional[int]:
        for operand in insn.operands:
            if operand.type == 2:  # MIPS immediate
                return operand.imm

        return None

    # -----------------------------------------------------------------
    # Get branch/jump destination
    # -----------------------------------------------------------------

    def _get_jump_target(self, insn) -> Optional[int]:

        if not insn.operands:
            return None

        # Direct branch/jump instructions have an immediate operand.
        for operand in insn.operands:

            if operand.type == 2:  # MIPS_OP_IMM
                return operand.imm

        return None


    def _get_source_registers(self, insn) -> list[str]:
        sources = []

        for i, operand in enumerate(insn.operands):

            # Normal register operand
            if operand.type == 1:
                reg = insn.reg_name(operand.reg)

                # First operand is the destination for our
                # register-writing instructions.
                if (
                    i == 0
                    and insn.mnemonic.lower() in REGISTER_WRITE_INSTRUCTIONS
                ):
                    continue

                sources.append(reg)

            # Memory operand
            elif operand.type == 3:
                # MIPS memory operand:
                #   base + displacement
                #
                # Example:
                #   lw $v0, 0($v0)
                #
                # operand.mem.base is the base register.

                base = operand.mem.base

                if base != 0:
                    sources.append(insn.reg_name(base))

        return sources



    def find_indirect_jump_tables(
        self,
        instructions: list[DecodedInstruction]
    ):
        switches = []

        for i in range(len(instructions) - 1):

            load = instructions[i]
            jump = instructions[i + 1]

            # Must end with:
            #
            #     lw   $reg, 0($reg)
            #     jr   $reg
            #

            if load.mnemonic not in {"lw", "lwu", "ld"}:
                continue

            if jump.mnemonic != "jr":
                continue

            if load.writes_register is None:
                continue

            target_reg = load.writes_register

            # A normal function return:
            #
            #     ld  $ra, ...
            #     jr  $ra
            #
            # is not a switch.
            if target_reg == "ra":
                continue

            # The register loaded by the LW must be the
            # register used by JR.
            if target_reg not in jump.source_registers:
                continue

            switches.append({
                "jump_address": jump.address,
                "target_register": target_reg,
                "load_address": load.address,
            })

        return switches

    def find_switch_table_base(
        self,
        instructions: list[DecodedInstruction],
        load_index: int,
        address_register: str,
    ) -> Optional[int]:

        # Search backwards from the LW.
        for i in range(load_index - 1, max(-1, load_index - 10), -1):

            insn = instructions[i]

            # We are looking for:
            #
            #     addu address_reg, index_reg, base_reg
            #
            if insn.mnemonic in {"addu", "daddu"}:
                if insn.writes_register != address_register:
                    continue

                # We need to inspect its source registers.
                if len(insn.source_registers) != 2:
                    continue

                # One source should be the index/address register.
                if address_register not in insn.source_registers:
                    continue

                # The other source is the table-base register.
                base_register = next(
                    r for r in insn.source_registers
                    if r != address_register
                )

                # Now search backwards for construction of base_register.
                table_base = self._resolve_register_constant(
                    instructions,
                    i,
                    base_register,
                )

                if table_base is not None:
                    return table_base

        return None

    def find_switches(
        self,
        instructions: list[DecodedInstruction],
    ):
        switches = []

        for i in range(len(instructions) - 1):

            load = instructions[i]
            jump = instructions[i + 1]

            # ---------------------------------------------------------
            # Look for:
            #
            #     lw   $reg, ($reg)
            #     jr   $reg
            # ---------------------------------------------------------

            if load.mnemonic not in {"lw", "lwu", "ld"}:
                continue

            if jump.mnemonic != "jr":
                continue

            if load.writes_register is None:
                continue

            target_reg = load.writes_register

            # Normal function return.
            if target_reg == "ra":
                continue

            # The register loaded by the LW must be the register
            # used by JR.
            if target_reg not in jump.source_registers:
                continue

            # ---------------------------------------------------------
            # Find the address calculation immediately before the LW.
            #
            #     addu target_reg, target_reg, base_reg
            #
            # ---------------------------------------------------------

            table_base = None
            base_register = None

            for j in range(i - 1, max(-1, i - 10), -1):

                calc = instructions[j]

                if calc.mnemonic not in {"addu", "daddu"}:
                    continue

                if calc.writes_register != target_reg:
                    continue

                if target_reg not in calc.source_registers:
                    continue

                # The other source register is the table-base register.
                other_registers = [
                    r for r in calc.source_registers
                    if r != target_reg
                ]

                if len(other_registers) != 1:
                    continue

                base_register = other_registers[0]

                table_base = self._resolve_register_constant(
                    instructions,
                    j,
                    base_register,
                )

                if table_base is not None:
                    break

            if table_base is None:
                continue

            switches.append({
                "jump_address": jump.address,
                "load_address": load.address,
                "target_register": target_reg,
                "index_register": target_reg,
                "table_base": table_base,
                "table_base_register": base_register,
            })

        return switches


    def _resolve_register_constant(
        self,
        instructions: list[DecodedInstruction],
        before_index: int,
        register: str,
    ) -> Optional[int]:

        addend = 0

        for i in range(before_index - 1, max(-1, before_index - 10), -1):

            insn = instructions[i]

            if insn.writes_register != register:
                continue

            # addiu reg, reg, imm
            if (
                insn.mnemonic == "addiu"
                and register in insn.source_registers
            ):
                if insn.immediate is None:
                    return None

                addend += insn.immediate
                continue

            # lui reg, imm
            if insn.mnemonic == "lui":
                if insn.immediate is None:
                    return None

                return ((insn.immediate << 16) + addend) & 0xFFFFFFFF

            # Something else overwrote the register.
            return None

        return None


    


    # -----------------------------------------------------------------
    # Find destination integer register
    # -----------------------------------------------------------------

    def _get_written_register(self, insn) -> Optional[str]:

        mnemonic = insn.mnemonic.lower()

        if mnemonic not in REGISTER_WRITE_INSTRUCTIONS:
            return None

        if not insn.operands:
            return None

        first_operand = insn.operands[0]

        # MIPS register operand
        if first_operand.type == 1:
            return insn.reg_name(first_operand.reg)

        return None

REGISTER_WRITE_INSTRUCTIONS = {
    # Arithmetic
    "addiu",
    "addi",
    "daddiu",
    "daddi",
    "add",
    "addu",
    "sub",
    "subu",
    "dadd",
    "daddu",
    "dsub",
    "dsubu",

    # Logical
    "and",
    "or",
    "xor",
    "nor",
    "andi",
    "ori",
    "xori",
    "lui",

    # Shifts
    "sll",
    "srl",
    "sra",
    "sllv",
    "srlv",
    "srav",
    "dsll",
    "dsrl",
    "dsra",
    "dsllv",
    "dsrlv",
    "dsrav",

    # Loads
    "lb",
    "lbu",
    "lh",
    "lhu",
    "lw",
    "lwu",
    "ld",
    "lwl",
    "lwr",
    "ldl",
    "ldr",

    # HI/LO
    "mfhi",
    "mflo",

    # Conditional moves
    "movn",
    "movz",

    # Pseudo-instruction
    "move",

    # Set-less-than
    "slt",
    "sltu",
    "slti",
    "sltiu",

    # Sign extension
    "seb",
    "seh",

    # Count leading bits
    "clz",
    "clo",
}

