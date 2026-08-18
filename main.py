import retrieve_function_bytes as fn
import constants
from decodeFunction import *
import controlFlow
from executeInstruction import execute_instruction

# source .decompile/bin/activate
# --- Usage Example ---
if __name__ == "__main__":
    # 1. Load the executable
    executable_path = "SLPS_255.47"
    wrapper = fn.SceneFunctionsWrapper(executable_path)
    decoder = MIPSDecoder()

    #try:
    if True:
        idx = 136#770
        func_va, func_name, func_bytes = wrapper.get_function_info(idx)

        instructions = decoder.decode(
            func_bytes,
            func_va,
            constants.interesting_jals
        )

        switches = decoder.find_switches(instructions)

        print(f"\nFunction: {func_name}")
        print(f"VA: {func_va:08X}\n")

        for insn in instructions:
            print(insn)
        print()
        
        for switch in switches:
            table = wrapper.read_switch_table(switch['table_base'])
            print(
                f"Switch found at "
                f"{switch['jump_address']:08X} "
                f"using {switch['target_register']} "
                f"table at {switch['table_base']:08X}"
            )
            print(table)


        print("Flow stuff \n")
        # Start all (relevant) registers at 0 with no instructions
        analyzer = controlFlow.ControlFlowAnalyzer(instructions)
        root = analyzer.analyze(func_va)
        controlFlow.print_graph(root)
        '''
        registers = controlFlow.create_initial_register_state()
        instructions_by_va = {instruct.address : instruct for instruct in instructions}
        controlFlow.start_traverse(func_va, instructions_by_va)

        state = registers
        for insn in instructions:

            if insn.address in {
                0x002BF094,
                0x002BF098,
                0x002BF09C,
                0x002BF0A0,
                0x002BF0A4,
            }:
                state = execute_instruction(
                    state,
                    insn,
                )

                print(
                    f"{insn.address:08X}: "
                    f"{insn.mnemonic:<6} "
                    f"{insn.op_str:<20}"
                )

                for reg in ["v0", "v1"]:
                    reg_state = state[reg]

                    low = (
                        f"{reg_state.low_instruction.address:08X}"
                        if reg_state.low_instruction
                        else "None"
                    )

                    high = (
                        f"{reg_state.high_instruction.address:08X}"
                        if reg_state.high_instruction
                        else "None"
                    )

                    print(
                        f"    {reg}: "
                        f"value={reg_state.value!r}, "
                        f"low={low}, "
                        f"high={high}"
                    )

        
        '''
    #except Exception as e:
    #    print(f"Error: {e}")





    '''
        for i, insn in enumerate(instructions):

            if (
                insn.mnemonic in {"addu", "daddu"}
                and insn.writes_register == "v0"
                and "v1" in insn.source_registers
            ):
                table_base = decoder._resolve_register_constant(
                    instructions,
                    i,
                    "v1",
                )

                print(
                    f"Possible switch table base: "
                    f"{table_base:#010x}"
                )

        for insn in instructions:
            if insn.mnemonic in {"lui", "addiu"}:
                print(
                    f"{insn.address:08X}: "
                    f"{insn.mnemonic:<6} "
                    f"{insn.op_str:<25} "
                    f"writes={insn.writes_register} "
                    f"reads={insn.source_registers} "
                    f"imm={insn.immediate:#x}"
                )

        print(f"Index:            {idx}")
        print(f"Function Name:  {func_name}")
        print(f"Virtual Address:{hex(func_va)}")
        print(f"File Offset:    {hex(wrapper.va_to_offset(va))}")
        print(f"Byte Count:        {len(func_bytes)} bytes")
        print(f"Machine Code:   {func_bytes.hex()}")
    '''