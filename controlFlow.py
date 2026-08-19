from dataclasses import dataclass, field
from decodeFunction import DecodedInstruction
from typing import Optional


class UnknownValue:
    def __repr__(self):
        return "UNKNOWN"

    def __str__(self):
        return "UNKNOWN"


UNKNOWN = UnknownValue()


def merge_value(a, b):
    if a == b:
        return a

    return UNKNOWN


MIPS_REGISTERS = [
    "zero",
    "at",
    "v0",
    "v1",
    "a0",
    "a1",
    "a2",
    "a3",
    "t0",
    "t1",
    "t2",
    "t3",
    "t4",
    "t5",
    "t6",
    "t7",
    "s0",
    "s1",
    "s2",
    "s3",
    "s4",
    "s5",
    "s6",
    "s7",
    "t8",
    "t9",
    "k0",
    "k1",
    "gp",
    "sp",
    "fp",
    "ra",
]

@dataclass
class RegisterState:
    value: object = 0

    # Last instruction that modified the low 32 bits
    low_instruction: object = None

    # Last instruction that modified the high 32 bits
    high_instruction: object = None


'''
class ExecutionNode:
    address: int

    registers: dict[str, RegisterState]

    instruction: Optional[DecodedInstruction] = None

    parent: Optional["ExecutionNode"] = None

    children: list["ExecutionNode"] = field(
        default_factory=list
    )
'''
@dataclass
class ExecutionNode:

    def __init__(
        self,
        address: int | None,
        registers: dict[str, RegisterState],
        instruction: "DecodedInstruction | None",
    ):
        self.address = address
        self.registers = registers
        self.instruction = instruction

        self.children = []
        self.parents = []
    '''
    def add_child(self, child):
        if child not in self.children:
            self.children.append(child)

        if self not in child.parents:
            child.parents.append(self)
    '''
    def add_child(self, child: "ExecutionNode"):
        for existing in self.children:
            if existing.address == child.address:
                return

        self.children.append(child)



def create_initial_register_state() -> dict[str, RegisterState]:
    return {
        register: RegisterState()
        for register in MIPS_REGISTERS
    }

def copy_register_state(
        registers: dict[str, RegisterState],
    ) -> dict[str, RegisterState]:

    return {
        register: RegisterState(
            value=state.value,
            low_instruction=state.low_instruction,
            high_instruction=state.high_instruction,
        )
        for register, state in registers.items()
    }

def merge_value(a, b):
    if a is UNKNOWN or b is UNKNOWN:
        return UNKNOWN

    if a == b:
        return a

    return UNKNOWN


def merge_register_state(
    a: RegisterState,
    b: RegisterState,
) -> RegisterState:

    return RegisterState(
        value=merge_value(a.value, b.value),
        low_instruction=merge_value(a.low_instruction, b.low_instruction),
        high_instruction=merge_value(a.high_instruction, b.high_instruction),
    )

def merge_registers(
    a: dict[str, RegisterState],
    b: dict[str, RegisterState],
) -> dict[str, RegisterState]:

    merged = {}

    for register in a:

        merged[register] = merge_register_state(
            a[register],
            b[register],
        )

    return merged


def registers_equal(
    a: dict[str, RegisterState],
    b: dict[str, RegisterState],
) -> bool:

    if a.keys() != b.keys():
        return False

    for register in a:

        ra = a[register]
        rb = b[register]

        if ra.value != rb.value:
            return False

        if ra.low_instruction != rb.low_instruction:
            return False

        if ra.high_instruction != rb.high_instruction:
            return False

    return True


def copy_registers(
    registers: dict[str, RegisterState],
) -> dict[str, RegisterState]:

    return {
        name: RegisterState(
            value=state.value,
            low_instruction=state.low_instruction,
            high_instruction=state.high_instruction,
        )
        for name, state in registers.items()
    }


def is_control_flow_instruction(
    insn: DecodedInstruction,
) -> bool:

    return insn.kind in {
        "branch",
        "jump",
        "indirect_branch",
        "return",
        "goto"
    }



def execute_delay_slot(
    node: ExecutionNode,
    instructions_by_va: dict[int, DecodedInstruction],
) -> dict[str, RegisterState]:

    registers = copy_register_state(node.registers)

    delay_address = node.address + 4

    delay_insn = instructions_by_va.get(
        delay_address
    )

    if delay_insn is None:
        return registers

    if delay_instruction.kind == "register_write":
        return execute_instruction(
            registers,
            delay_instruction,
        )

    return registers

def create_child(
    parents: list[ExecutionNode],
    address: int,
    registers: dict[str, RegisterState],
    instruction: Optional[DecodedInstruction],
) -> ExecutionNode:

    child = ExecutionNode(
        address=address,
        registers=registers,
        instruction=instruction,
        parent=parent,
    )

    parent.children.append(child)

    return child


def traverse_branch(
    node: ExecutionNode,
    instructions_by_va: dict[int, DecodedInstruction],
):

    insn = node.instruction

    # Execute the delay slot first.
    registers_after_delay = self.execute_delay_slot(
        node,
        instructions_by_va,
    )

    # Branch target
    target = insn.jump_target

    if target is not None:

        target_insn = instructions_by_va.get(target)

        if target_insn is not None:

            self.create_child(
                parent=node,
                address=target,
                registers=copy_register_state(
                    registers_after_delay
                ),
                instruction=target_insn,
            )

    # Fall-through skips both the branch and delay slot.
    fallthrough_address = node.address + 8

    fallthrough_insn = instructions_by_va.get(
        fallthrough_address
    )

    if fallthrough_insn is not None:

        self.create_child(
            parent=node,
            address=fallthrough_address,
            registers=copy_register_state(
                registers_after_delay
            ),
            instruction=fallthrough_insn,
        )

def traverse_sequential(
    root: ExecutionNode,
    instructions_by_va: dict[int, DecodedInstruction],
):
    node = root

    while True:

        insn = instructions_by_va.get(node.address)
        #print(insn)
        if insn is None:
            break

        print(
            f"{insn.address:08X}: "
            f"{insn.mnemonic:<8} "
            f"{insn.op_str}"
        )

        new_registers = execute_instruction(
            node.registers,
            insn,
        )

        next_address = insn.address + 4
        next_insn = instructions_by_va.get(next_address)

        if next_insn is None:
            break

        child = self.create_child(
            parent=node,
            address=next_address,
            registers=new_registers,
            instruction=next_insn,
        )

        node = child

def start_traverse(
    func_va,
    instructions_by_va: dict[int, DecodedInstruction],
):
    root = ExecutionNode(
        address=None,
        registers=create_initial_register_state(),
        instruction=None,
    )
    print(func_va)
    print(instructions_by_va)
    first_instruction = instructions_by_va[func_va]

    root.children.append(
        ExecutionNode(
            address=func_va,
            registers=copy_register_state(root.registers),
            instruction=first_instruction,
            parent=root,
        )
    )


    traverse_sequential(root.children[0], instructions_by_va)



class ControlFlowAnalyzer:

    def __init__(
        self,
        instructions: list[DecodedInstruction],
    ):
        self.instructions_by_va = {
            insn.address: insn
            for insn in instructions
        }

        self.nodes_by_va: dict[int, ExecutionNode] = {}


    def get_or_create_node(
        self,
        parent: ExecutionNode | None,
        address: int,
        registers: dict[str, RegisterState],
    ) -> tuple[ExecutionNode, bool]:

        instruction = self.instructions_by_va.get(address)

        if instruction is None:
            raise ValueError(
                f"No instruction at {address:08X}"
            )

        # ---------------------------------------------------------
        # Node already exists
        # ---------------------------------------------------------

        existing = self.nodes_by_va.get(address)

        if existing is not None:

            old_registers = existing.registers

            merged = merge_registers(
                existing.registers,
                registers,
            )

            changed = not registers_equal(
                existing.registers,
                merged,
            )

            existing.registers = merged

            if parent is not None:
                parent.add_child(existing)

            return existing, changed

        # ---------------------------------------------------------
        # New node
        # ---------------------------------------------------------

        node = ExecutionNode(
            address=address,
            registers=copy_registers(registers),
            instruction=instruction,
        )

        self.nodes_by_va[address] = node

        if parent is not None:
            parent.add_child(node)

        return node, True


    def execute_delay_slot(
        self,
        node: ExecutionNode,
    ) -> dict[str, RegisterState]:

        registers = copy_registers(
            node.registers
        )

        delay_address = node.address + 4

        delay_instruction = self.instructions_by_va.get(
            delay_address
        )

        if delay_instruction is None:
            return registers

        return execute_instruction(
            registers,
            delay_instruction,
        )

    def process_sequential(
        self,
        node: ExecutionNode,
    ) -> list[tuple[ExecutionNode, dict[str, RegisterState]]]:

        registers = execute_instruction(
            node.registers,
            node.instruction,
        )

        next_address = node.address + 4

        next_instruction = self.instructions_by_va.get(
            next_address
        )

        if next_instruction is None:
            return []

        return [
            (
                node,
                registers,
            )
        ]

    def analyze(
        self,
        function_va: int,
    ) -> ExecutionNode:

        initial_registers = create_initial_register_state()

        root = ExecutionNode(
                address=function_va,
                registers=copy_registers(initial_registers),
                instruction=None,
            )
        first_node, _ = self.get_or_create_node(
                parent=root,
                address=function_va,
                registers=initial_registers,
            )

        worklist = [first_node]

        while worklist:

            node = worklist.pop()

            successors = self.process_node(node)
            '''
            print(
                f"{node.address:08X} -> "
                f"{[(hex(child.address), changed) for child, changed in successors]}"
            )
            '''

            for successor, changed in successors:

                if changed:
                    worklist.append(successor)

        return root

    
    def process_branch(
        self,
        node: ExecutionNode,
    ):

        insn = node.instruction

        # Branch condition is deliberately NOT evaluated.
        # We explore every possible outcome.

        registers = self.execute_delay_slot(node)

        successors = []

        # ---------------------------------------------------------
        # Taken path
        # ---------------------------------------------------------

        if insn.jump_target is not None:

            target, changed = self.get_or_create_node(
                parent=node,
                address=insn.jump_target,
                registers=registers,
            )

            successors.append(
                (target, changed)
            )

        # ---------------------------------------------------------
        # Fall-through path
        # ---------------------------------------------------------

        fallthrough_address = node.address + 8

        if fallthrough_address in self.instructions_by_va:

            child, changed = self.get_or_create_node(
                parent=node,
                address=fallthrough_address,
                registers=copy_registers(registers),
            )

            successors.append((child, changed))


        print(
            f"BRANCH {node.address:08X} CHILDREN:",
            [f"{child.address:08X}" for child in node.children]
        )

        return successors
        return successors
    


    def process_jal(
        self,
        node: ExecutionNode,
    ):
        insn = node.instruction

        # Execute the JAL delay slot.
        registers = self.execute_delay_slot(node)

        # We do NOT follow insn.jump_target.
        # The called function is outside this traversal.

        next_address = node.address + 8

        next_insn = self.instructions_by_va.get(
            next_address
        )

        if next_insn is None:
            return []

        child, changed = self.get_or_create_node(
            parent=node,
            address=next_address,
            registers=registers,
        )

        return [
            (child, changed)
        ]

    def process_goto(
        self,
        node: ExecutionNode,
    ):

        insn = node.instruction

        # Execute the delay slot.
        registers = self.execute_delay_slot(node)

        if insn.jump_target is None:
            raise ValueError(
                f"Goto at {node.address:08X} "
                f"has no jump target"
            )

        child, changed = self.get_or_create_node(
            parent=node,
            address=insn.jump_target,
            registers=registers,
        )

        return [
            (child, changed)
        ]

    def process_return(
        self,
        node: ExecutionNode,
    ):
        # The jr ra has a delay slot, so execute it.
        #
        # There is no successor because we are analyzing
        # only this function.
        self.execute_delay_slot(node)

        return []

    def process_indirect_jump(
        self,
        node: ExecutionNode,
    ):
        raise NotImplementedError(
            f"Indirect jump at "
            f"{node.address:08X} is not a return "
            f"and switch handling has not been implemented yet."
        )

    def process_node(self, node: ExecutionNode):

        insn = node.instruction

        if insn is None:
            return []

        if insn.kind == "branch":
            return self.process_branch(node)

        if insn.kind == "goto":
            return self.process_goto(node)

        if insn.kind == "jal":
            return self.process_jal(node)

        if insn.kind == "indirect_jump":
            return []

        if insn.kind == "indirect_branch":
            # jr ra = function return
            if insn.mnemonic.lower() == "jr" and \
               insn.op_str.strip() == "$ra":

                return self.process_return(node)

            # Other indirect jumps are currently switches.
            return self.process_indirect_jump(node)

        if insn.kind == "register_write":
            registers = execute_instruction(
                node.registers,
                insn,
            )

        elif insn.kind == "other":
            registers = copy_registers(
                node.registers
            )

        else:
            raise ValueError(
                f"Unknown instruction kind: {insn.kind}"
            )

        next_address = node.address + 4

        next_insn = self.instructions_by_va.get(
            next_address
        )

        if next_insn is None:
            return []

        child, changed = self.get_or_create_node(
            parent=node,
            address=next_address,
            registers=registers,
        )

        return [(child, changed)]





def print_graph(root: ExecutionNode):

    visited = set()

    def visit(node: ExecutionNode, depth: int):

        indent = ""#"    " * depth

        if node.instruction is None:
            print(f"{indent}ROOT")
        else:
            print(
                f"{indent}{node.address:08X}: "
                f"{node.instruction.op_str}"
            )

        node_id = id(node)

        if node_id in visited:
            print(f"{indent}    [already visited]")
            return

        visited.add(node_id)

        for reg, state in node.registers.items():
            if (
                state.value != 0
                or state.low_instruction is not None
                or state.high_instruction is not None
            ):
                print(
                    f"{indent}    "
                    f"{reg}: value={state.value if state.value is UNKNOWN or state.value is None else hex(state.value)}, "
                    f"low={state.low_instruction}, "
                    f"high={state.high_instruction}"
                )

        for child in node.children:
            visit(child, depth + 1)

    visit(root, 0)



#--------------------------------------------------------------------------#
#                       This section is for instructions only              #
#--------------------------------------------------------------------------#
MASK32 = 0xFFFFFFFF
MASK64 = 0xFFFFFFFFFFFFFFFF

def write_high16(
    registers: dict[str, RegisterState],
    register: str,
    value: int,
    insn: DecodedInstruction,
):
    if register == "zero":
        return

    state = registers[register]

    if value is UNKNOWN:
        state.value = UNKNOWN
        state.high_instruction = insn
        state.low_instruction = None
        return

    state.value = (
        (value & 0xFFFF) << 16
    ) & MASK32

    state.high_instruction = insn
    state.low_instruction = None


def write_addiu(
    registers: dict[str, RegisterState],
    register: str,
    value: int | object,
    insn: DecodedInstruction,
):
    if register == "zero":
        return

    state = registers[register]

    if value is UNKNOWN:
        state.value = UNKNOWN
        state.low_instruction = insn
        state.high_instruction = None
        return

    value &= MASK32

    state.value = value
    state.low_instruction = insn

def sign_extend_32(value: int) -> int:
    if value is UNKNOWN:
        return UNKNOWN
    value &= MASK32

    if value & 0x80000000:
        return value - 0x100000000

    return value

def unsigned_32(value: int) -> int:
    if value is UNKNOWN:
        return UNKNOWN
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
    if state.value is not UNKNOWN and value is not UNKNOWN:
        state.value = (
            state.value & 0xFFFFFFFF00000000
        ) | (value & MASK32)
    else:
        state.value = UNKNOWN

    state.low_instruction = insn
    state.high_instruction = insn

def write_64(
    registers: dict[str, RegisterState],
    register: str,
    value: int,
    insn: DecodedInstruction,
):
    if register == "zero":
        return

    state = registers[register]
    if state.value is not UNKNOWN and value is not UNKNOWN:
        state.value = value & MASK64
    else:
        state.value = UNKNOWN

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
    state.high_instruction = insn

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

def unknown_if_any(*values):
    return any(value is UNKNOWN for value in values)

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

            write_high16(
                new_registers,
                dest,
                insn.immediate,
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

            if unknown_if_any(source_value):
                result = UNKNOWN
            else:
                result = (
                    source_value +
                    insn.immediate
                ) & MASK32

            write_addiu(
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

            if unknown_if_any(lhs, rhs):
                result = UNKNOWN
            else:
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
            if unknown_if_any(source):
                result = UNKNOWN
            else:
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

            if unknown_if_any(lhs, rhs):
                result = UNKNOWN
            else:
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

            if unknown_if_any(source):
                result = UNKNOWN
            else:
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

            if unknown_if_any(lhs, rhs):
                result = UNKNOWN
            else:
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

            if unknown_if_any(source):
                result = UNKNOWN
            else:
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
            if unknown_if_any(source_value):
                result = UNKNOWN
            else:
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