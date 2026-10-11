from dataclasses import dataclass, field
from decodeFunction import DecodedInstruction
from typing import Optional
from constants import check_if_important_jal, function_registers, check_if_important_jal_int, UnknownValue
from retrieve_function_bytes import SceneFunctionsWrapper
import struct




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


@dataclass
class FunctionCall:
    call_address: int
    function_address: int
    registers: dict[str, RegisterState]



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

'''
@dataclass
class CallNode:
    address: int
    function_address: int
    registers: dict[str, RegisterState]

    # Edges to other important calls
    children: list["CallNode"] = field(default_factory=list)

    execution_node: ExecutionNode | None = None

    def add_child(self, child: "CallNode"):

        for existing in self.children:
            if existing.address == child.address:
                return

        self.children.append(child)
'''
@dataclass
class CallNode:
    call: FunctionCall
    children: list["CallNode"] = field(default_factory=list)

    def add_child(self, child: "CallNode"):
        if child not in self.children:
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

def copy_one_register(state: RegisterState):
    return RegisterState(
            value=state.value,
            low_instruction=state.low_instruction,
            high_instruction=state.high_instruction,
        )


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
        function_va,
        function_name,
        function_id,
        instructions: list[DecodedInstruction],
        wrapper
    ):
        self.function_va = function_va
        self.function_name = function_name
        self.number = function_id
        self.instructions_by_va = {
            insn.address: insn
            for insn in instructions
        }
        self.wrapper = wrapper

        self.nodes_by_va: dict[int, ExecutionNode] = {}

        self.switches = self.find_switches(instructions)
        self.switches_by_jump_va = {
            switch["jump_address"] : switch
            for switch in self.switches
        }

        self.function_calls = []
        self.call_nodes_by_address = {}
        self.call_graph_root = None


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
    ) -> ExecutionNode:

        initial_registers = create_initial_register_state()

        root = ExecutionNode(
                address=self.function_va,
                registers=copy_registers(initial_registers),
                instruction=None,
            )
        first_node, _ = self.get_or_create_node(
                parent=root,
                address=self.function_va,
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

    
    def get_state_after_delay_slot(
        self,
        node: ExecutionNode,
    ) -> dict[str, RegisterState]:

        if node.instruction is None:
            return copy_registers(node.registers)

        delay_address = node.address + 4

        delay_insn = self.instructions_by_va.get(delay_address)

        if delay_insn is None:
            raise ValueError(
                f"Missing delay slot at {delay_address:08X}"
            )

        registers = copy_registers(node.registers)

        if delay_insn.kind == "register_write":
            registers = execute_instruction(
                registers,
                delay_insn,
            )

        return registers


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

        '''
        print(
            f"BRANCH {node.address:08X} CHILDREN:",
            [f"{child.address:08X}" for child in node.children]
        )
        '''

        return successors
        return successors
    


    def process_jal(self, node: ExecutionNode):

        insn = node.instruction

        if insn is None or insn.kind != "jal":
            return []

        # Execute the JAL delay slot.
        registers = self.execute_delay_slot(node)
        state_after_slot = self.get_state_after_delay_slot(node)

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


        function_address = insn.jump_target

        if check_if_important_jal_int(function_address):
            # ---------------------------------------------------------
            # Extract only the registers required by this function
            # ---------------------------------------------------------

            required_registers = function_registers[
                function_address
            ]["registers"]

            call_registers = {
                register: copy_one_register(
                    state_after_slot[register]
                )
                for register in required_registers
            }

            # ---------------------------------------------------------
            # Save the call
            # ---------------------------------------------------------

            call = FunctionCall(
                call_address=insn.address,
                function_address=function_address,
                registers=call_registers,
            )

            try_find = filter(lambda x: x.call_address == call.call_address , self.function_calls)
            if len(list(try_find)) == 0:
                self.function_calls.append(call)



            
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

    def _resolve_register_constant(
        self,
        instructions: list[DecodedInstruction],
        before_index: int,
        register: str,
    ) -> Optional[int]:

        addend = 0

        for i in range(
            before_index - 1,
            max(-1, before_index - 10),
            -1
        ):

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

                return (
                    (insn.immediate << 16) + addend
                ) & 0xFFFFFFFF

            # Something else overwrote the register.
            return None

        return None

    def find_switch_table_base(
        self,
        instructions: list[DecodedInstruction],
        load_index: int,
        address_register: str,
    ) -> Optional[int]:

        # Search backwards from the LW.
        for i in range(
            load_index - 1,
            max(-1, load_index - 10),
            -1
        ):

            insn = instructions[i]

            # We are looking for:
            #
            #     addu address_reg, index_reg, base_reg
            #
            if insn.mnemonic not in {"addu", "daddu"}:
                continue

            if insn.writes_register != address_register:
                continue

            if len(insn.source_registers) != 2:
                continue

            if address_register not in insn.source_registers:
                continue

            # The other source is the table-base register.
            base_register = next(
                r for r in insn.source_registers
                if r != address_register
            )

            table_base = self._resolve_register_constant(
                instructions,
                i,
                base_register,
            )

            if table_base is not None:
                return table_base

        return Nones

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

            # jr ra is a normal function return.
            if target_reg == "ra":
                continue

            # The register loaded by LW must be the register
            # used by JR.
            if target_reg not in jump.source_registers:
                continue

            # ---------------------------------------------------------
            # Find the address calculation before LW:
            #
            #     addu target_reg, target_reg, base_reg
            #
            # ---------------------------------------------------------

            table_base = None
            base_register = None

            for j in range(
                i - 1,
                max(-1, i - 10),
                -1
            ):

                calc = instructions[j]

                if calc.mnemonic not in {"addu", "daddu"}:
                    continue

                if calc.writes_register != target_reg:
                    continue

                if target_reg not in calc.source_registers:
                    continue

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

    def read_switch_table(
        self,
        table_base: int,
        count: int = 16,
    ) -> list[int]:

        targets = []

        for i in range(count):

            entry_va = table_base + i * 4

            offset = self.wrapper.va_to_offset(entry_va)

            raw = self.wrapper.data[
                offset:offset + 4
            ]

            if len(raw) != 4:
                raise ValueError(
                    f"Could not read switch entry "
                    f"at {entry_va:08X}"
                )

            target = struct.unpack(
                "<I",
                raw
            )[0]

            targets.append(target)

        return targets


    def process_indirect_jump(
        self,
        node: ExecutionNode,
    ):

        insn = node.instruction

        if insn is None:
            return []

        # ---------------------------------------------------------
        # Find the switch corresponding to this JR.
        # ---------------------------------------------------------

        switch = self.switches_by_jump_va.get(
            node.address
        )

        if switch is None:
            raise ValueError(
                f"Could not find switch table for "
                f"indirect jump at {node.address:08X}"
            )

        # ---------------------------------------------------------
        # Execute the delay slot.
        # ---------------------------------------------------------

        delay_address = node.address + 4

        delay_insn = self.instructions_by_va.get(
            delay_address
        )

        if delay_insn is None:
            raise ValueError(
                f"Missing delay slot at "
                f"{delay_address:08X}"
            )

        registers = copy_registers(node.registers)

        if delay_insn.kind == "register_write":
            registers = execute_instruction(
                registers,
                delay_insn,
            )

        elif delay_insn.kind == "other":
            pass

        else:
            raise ValueError(
                f"Unexpected delay-slot instruction at "
                f"{delay_address:08X}: "
                f"{delay_insn.mnemonic}"
            )

        # ---------------------------------------------------------
        # Read all switch destinations.
        # ---------------------------------------------------------

        targets = self.read_switch_table(
            switch["table_base"],
            count=16,
        )

        # ---------------------------------------------------------
        # Create one child for every possible case.
        # ---------------------------------------------------------

        successors = []

        for target in targets:

            child, changed = self.get_or_create_node(
                parent=node,
                address=target,
                registers=copy_registers(registers),
            )

            successors.append(
                (child, changed)
            )

        return successors


    def read_switch_table(
        self,
        table_va: int,
        count: int = 16
    ) -> list[int]:

        targets = []

        for i in range(count):

            entry_va = table_va + i * 4

            offset = self.wrapper.va_to_offset(
                entry_va
            )

            target = struct.unpack(
                "<I",
                self.wrapper.data[offset:offset + 4],
            )[0]

            targets.append(target)

        return targets

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


    def get_dialogue_info(self, root: ExecutionNode, dialogue_dict = {}):
        visited = set()

        def visit(node: ExecutionNode, depth: int):
            
            node_id = id(node)
            
            if node_id in visited:
                #print(f"{indent}    [already visited]")
                return

            visited.add(node_id)
            if node.instruction is not None and check_if_important_jal(node.instruction.op_str):
                registers = self.get_state_after_delay_slot(node)
                # We get the dialogue

                dialogue_address = registers.get('a0').value
                calls_list = dialogue_dict.get(dialogue_address)
                if calls_list is None:
                    dialogue_dict[dialogue_address] = []
                dialogue_dict[dialogue_address].append(node.address)


            for child in node.children:
                visit(child, depth + 1)

        visit(root, 0)


        return dialogue_dict


    def print_graph(self, root: ExecutionNode):

        visited = set()

        def visit(node: ExecutionNode, depth: int):
            
            indent = ""#"    " * depth
            '''
            if node.instruction is None:
                print(f"{indent}ROOT")
            else:
                print(
                    f"{indent}{node.address:08X}: "
                    f"{node.instruction.op_str}"
                )
            '''
            node_id = id(node)
            
            if node_id in visited:
                #print(f"{indent}    [already visited]")
                return

            visited.add(node_id)
            if node.instruction is not None and check_if_important_jal(node.instruction.op_str):
                registers = self.get_state_after_delay_slot(node)
                # We get the dialogue
                print(f"{node.address:08X}")
                print(self.wrapper.read_string_at_va(registers.get('a0').value))

                '''
                for reg, state in registers.items():
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
                '''

            for child in node.children:
                visit(child, depth + 1)

        visit(root, 0)


    def build_call_graph(self, execution_root: ExecutionNode):

        # ---------------------------------------------------------
        # Every important JAL discovered during execution analysis.
        # ---------------------------------------------------------

        calls_by_address = {
            call.call_address: call
            for call in self.function_calls
        }

        # ---------------------------------------------------------
        # Create one CallNode for every FunctionCall.
        # ---------------------------------------------------------

        call_nodes = {
            address: CallNode(call=call)
            for address, call in calls_by_address.items()
        }

        # ---------------------------------------------------------
        # Find the important JALs that are reachable from each
        # execution path.
        # ---------------------------------------------------------

        visited = set()

        def find_calls(
            node: ExecutionNode,
            previous_call: CallNode | None,
        ):

            # The state of the traversal includes the previous call.
            #
            # This matters because execution nodes can merge.
            key = (
                id(node),
                id(previous_call) if previous_call is not None else None,
            )

            if key in visited:
                return

            visited.add(key)

            # -----------------------------------------------------
            # Is this an important JAL?
            # -----------------------------------------------------

            call = calls_by_address.get(node.address)

            if call is not None:

                current_call = call_nodes[node.address]

                # If we reached this JAL from another important JAL,
                # connect them.
                if previous_call is not None:
                    previous_call.add_child(current_call)

                previous_call = current_call

            # -----------------------------------------------------
            # Continue through ALL execution children.
            # -----------------------------------------------------

            for child in node.children:
                find_calls(
                    child,
                    previous_call,
                )

        find_calls(
            execution_root,
            None,
        )

        # ---------------------------------------------------------
        # Find root calls.
        #
        # A CallNode is a root if nothing points to it.
        # ---------------------------------------------------------

        has_parent = set()

        for node in call_nodes.values():
            for child in node.children:
                has_parent.add(id(child))

        roots = [
            node
            for node in call_nodes.values()
            if id(node) not in has_parent
        ]

        return roots, call_nodes


    def print_call_graph(self, roots):

        visited = set()

        def visit(node: CallNode, depth: int):

            indent = "    " * depth

            call = node.call

            print(
                f"{indent}JAL {call.call_address:08X} "
                f"-> {call.function_address:08X}"
            )

            for register, state in call.registers.items():

                if state.value is UNKNOWN:
                    value = "UNKNOWN"
                else:
                    value = f"0x{state.value:X}"

                print(
                    f"{indent}    "
                    f"{register} = {value}"
                )

            node_id = id(node)

            if node_id in visited:
                print(
                    f"{indent}    [already visited]"
                )
                return

            visited.add(node_id)

            for child in node.children:
                visit(child, depth + 1)

        for root in roots:
            visit(root, 0)

    # --------------------------------------  Dialogue stuff ---------------------------------------
    def extract_dialogue_from_call(self, call):
        definition = function_registers.get(call.function_address)
        if definition is None:
            return None

        dialogues = []

        #print(hex(call.call_address))
        for register in definition["dialogue"]:
            state = call.registers.get(register)

            if state is None:
                raise ValueError(
                    f"Missing register {register} for "
                    f"call at {call.call_address:08X}"
                )

            if state.value is UNKNOWN:
                raise ValueError(
                    f"UNKNOWN value in {register} for "
                    f"call at {call.call_address:08X}"
                )

            text_address = state.value
            #print("   "+ hex(text_address))
            if text_address == 0:
                # Special case
                dialogues.append({
                    "register": register,
                    "call_address": call.call_address,
                    "function_address": call.function_address,
                    "text_address": 0,
                    "original": "",
                })
                continue
            try:
                original = self.wrapper.read_string_at_va(text_address)
            except (ValueError, IndexError):
                raise ValueError(
                    f"Invalid dialogue address "
                    f"{text_address:08X} at call {call.call_address:08X}"
                )

            dialogues.append({
                "register": register,
                "call_address": call.call_address,
                "function_address": call.function_address,
                "text_address": text_address,
                "original": original,
            })

        return dialogues


    def extract_scene_dialogues(self):
        analysis = self.analyze()

        dialogues = []

        for call in self.function_calls:
            try:
                dialogue = self.extract_dialogue_from_call(call)
            except:
                dialogue = "COULDN'T PROCESS IT"
                print(call)

            if dialogue is not None:
                dialogues.append(dialogue)

        return dialogues

    def extract_scene_information(self):
        analysis = self.analyze()

        calls = []

        for call in self.function_calls:
            call_info = self.extract_call(call)

            if call_info is not None:
                calls.append(call_info)

        return calls

    def extract_call(self, call):
        definition = function_registers.get(call.function_address)

        if definition is None:
            return None

        registers = {}

        for register in definition["registers"]:
            state = call.registers.get(register)

            if state is None:
                raise ValueError(
                    f"Missing {register} at call "
                    f"{call.call_address:08X}"
                )

            registers[register] = {
                "value": state.value,
                "low_instruction": (
                    state.low_instruction.address
                    if state.low_instruction and state.low_instruction != UNKNOWN else None
                ),
                "high_instruction": (
                    state.high_instruction.address
                    if state.high_instruction and state.high_instruction != UNKNOWN else None
                ),
            }

        dialogues = []

        for register in definition["dialogue"]:
            state = call.registers[register]

            if state.value is UNKNOWN:
                raise ValueError(
                    f"UNKNOWN dialogue register {register} at "
                    f"{call.call_address:08X}"
                )

            text_address = state.value
            if text_address == 0:
                dialogues.append({
                    "register": register,
                    "text_address": text_address,
                    "original": "",
                })
                continue
            try:
                original = self.wrapper.read_string_at_va(text_address)
            except:
                original = "COULDN'T PROCESS IT"

            dialogues.append({
                "register": register,
                "text_address": text_address,
                "original": original,
                "en": "",
                "es": ""
            })

        return {
            "call_address": call.call_address,
            "function_address": call.function_address,
            "registers": registers,
            "dialogues": dialogues,
        }




    def extract_scene(self):
        analysis = self.analyze()

        calls = []

        for call in self.function_calls:
            extracted = self.extract_call(call)

            if extracted is not None:
                calls.append(extracted)

        return {
            "scene": self.number,
            "name": self.function_name,
            "calls": calls,
        }

    

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
    if state.value is not UNKNOWN and value is not UNKNOWN \
    and state.value is not None and value is not None:
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


    
        