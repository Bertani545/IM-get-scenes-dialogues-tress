import retrieve_function_bytes as fn
import constants
from decodeFunction import *


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Load the executable
    executable_path = "SLPS_255.47"
    wrapper = fn.SceneFunctionsWrapper(executable_path)
    decoder = MIPSDecoder()

    try:
        idx = 770
        func_va, func_name, func_bytes = wrapper.get_function_info(idx)

        instructions = decoder.decode(
            func_bytes,
            func_va,
            constants.interesting_jals
        )

        switches = decoder.find_indirect_jump_tables(instructions)

        print(f"\nFunction: {func_name}")
        print(f"VA: {func_va:08X}\n")

        for insn in instructions:
            print(insn)
        print()
        
        for i, insn in enumerate(instructions):
            if insn.mnemonic == "jr":
                print("\nPossible indirect jump:")

                start = max(0, i - 5)
                end = min(len(instructions), i + 2)

                for x in instructions[start:end]:
                    print(
                        f"  {x.address:08X}: "
                        f"{x.mnemonic:<8} "
                        f"{x.op_str:<20} "
                        f"writes={x.writes_register} "
                        f"reads={x.source_registers}"
                    )
        for switch in switches:
            print(
                f"Switch found at "
                f"{switch['jump_address']:08X} "
                f"using {switch['target_register']}"
            )
        '''
        print(f"Index:            {idx}")
        print(f"Function Name:  {func_name}")
        print(f"Virtual Address:{hex(func_va)}")
        print(f"File Offset:    {hex(wrapper.va_to_offset(va))}")
        print(f"Byte Count:        {len(func_bytes)} bytes")
        print(f"Machine Code:   {func_bytes.hex()}")
        '''

    except Exception as e:
        print(f"Error: {e}")