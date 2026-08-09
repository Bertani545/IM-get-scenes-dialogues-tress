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

    def __str__(self):
        return (
            f"{self.address:08X}: "
            f"{self.mnemonic:<8} {self.op_str:<25} "
            f"[{self.kind}]"
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

                        if jump_target is not None and jump_target in interesting_jals:
                            instructions.append(
                                DecodedInstruction(
                                    address=insn.address,
                                    mnemonic=insn.mnemonic,
                                    op_str=insn.op_str,
                                    bytes=bytes(insn.bytes),
                                    kind="jal",
                                    jump_target=jump_target,
                                    source_registers=self._get_source_registers(insn)
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
                            source_registers=self._get_source_registers(insn)
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
                            source_registers=self._get_source_registers(insn)
                        )
                    )
                    continue
            

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
        """
        Returns the GPRs read by an instruction.

        We deliberately use the operand structure rather than parsing
        op_str, since Capstone may represent pseudo-instructions
        differently.
        """

        sources = []

        for i, operand in enumerate(insn.operands):

            if operand.type != 1:  # MIPS register
                continue

            reg = insn.reg_name(operand.reg)

            # The first operand of our register-writing instructions
            # is normally the destination.
            if i == 0 and insn.mnemonic.lower() in REGISTER_WRITE_INSTRUCTIONS:
                continue

            sources.append(reg)

        return sources



    def find_indirect_jump_tables(
        self,
        instructions: list[DecodedInstruction]
    ):
        switches = []

        for i in range(len(instructions) - 1):

            load = instructions[i]
            jump = instructions[i + 1]

            # Must be:
            #
            #   lw  $reg, 0($reg)
            #   jr  $reg
            #

            if load.mnemonic not in {"lw", "lwu", "ld"}:
                continue

            if jump.mnemonic != "jr":
                continue

            if load.writes_register is None:
                continue

            target_reg = load.writes_register

            # jr must use the register loaded above.
            if target_reg not in jump.source_registers:
                continue

            # We specifically want offset 0 here.
            if load.op_str.split(",")[1].strip() not in {
                f"0({target_reg})",
                f"0x0({target_reg})",
            }:
                continue

            switches.append({
                "jump_address": jump.address,
                "target_register": target_reg,
                "load_address": load.address,
            })

        return switches
        

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

