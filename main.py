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

    idx = 50
    dialogues = dict()
    func_va, func_name, func_bytes = wrapper.get_function_info(idx)
    instructions = decoder.decode(
        func_bytes,
        func_va,
        constants.function_registers
    )
    analyzer = controlFlow.ControlFlowAnalyzer(func_va, func_name, instructions, wrapper)
    root = analyzer.analyze(func_va)
    analyzer.get_dialogue_info(root, dialogues)
    analyzer.print_graph(root)
    

    roots, call_nodes = analyzer.build_call_graph(root)
    #print(roots)
    analyzer.print_call_graph(roots)


    #print(jal_root)
    try:
        print()

        #analyzer.get_dialogue_info(root, wrapper, dialogues)
        #analyzer.print_graph(root, wrapper)
        #print(f"{func_name}")
    except:
        print(f"Error con la función {idx}, {func_name}, {func_va}")

    '''
    dialogues = dict()
    for idx in range(1,796):
        try:
            func_va, func_name, func_bytes = wrapper.get_function_info(idx)
            instructions = decoder.decode(
                func_bytes,
                func_va,
                constants.function_registers
            )
            analyzer = controlFlow.ControlFlowAnalyzer(instructions, wrapper)
            root = analyzer.analyze(func_va)

            analyzer.get_dialogue_info(root, wrapper, dialogues)
            #analyzer.print_graph(root, wrapper)
            #print(f"{func_name}")
        except:
            print(f"Error con la función {idx}, {func_name}, {func_va}")

    for dialogue_va, calls_list in dialogues.items():
        if dialogue_va is None:
            print(calls_list)
            continue
        if len(calls_list) > 1:
            print(wrapper.read_string_at_va(dialogue_va))
            print(f"Called {len(calls_list)}")
    '''

    #try:
    if False:
        idx = 749#136#770
        func_va, func_name, func_bytes = wrapper.get_function_info(idx)

        instructions = decoder.decode(
            func_bytes,
            func_va,
            constants.function_registers
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
        
        analyzer = controlFlow.ControlFlowAnalyzer(instructions, wrapper)
        root = analyzer.analyze(func_va)

        analyzer.print_graph(root, wrapper)
