import struct
import constants

class SceneFunctionsWrapper:
	def __init__(self, filepath: str):
		self.filepath = filepath
		constants.VA_OFFSET = 0xFFF80
		self.scene_array_va = 0x3071F0
		self.n_functions = 797
		self.n_effective_function = 796
		
		# Load the executable raw bytes into memory
		with open(filepath, 'rb') as f:
			self.data = f.read()


	def va_to_offset(self, va: int) -> int:
		"""Converts Virtual Address to raw file offset using the offset rule."""
		offset = va - constants.VA_OFFSET
		if offset < 0 or offset >= len(self.data):
			raise ValueError(f"Virtual address {hex(va)} maps to out-of-bounds offset {hex(offset)}")
		return offset

	def read_string_at_va(self, va: int) -> str:
		"""Reads a null-terminated ASCII string from a given virtual address.
			For retrieving the function names"""
		offset = self.va_to_offset(va)
		end = self.data.find(b'\x00', offset)
		if end == -1:
			raise ValueError(f"Null-terminator not found for string at VA {hex(va)}")
		return self.data[offset:end].decode('shift_jis', errors='replace')

	def read_string_and_get_metadata(self, va: int)-> (str, str):
		"""Reads a null-terminated ASCII string from a given virtual address.
			Then checks for metada"""
		offset = self.va_to_offset(va)
		end = self.data.find(b'\x00', offset)
		if end == -1:
			raise ValueError(f"Null-terminator not found for string at VA {hex(va)}")
		text = self.data[offset:end].decode('shift_jis', errors='replace')
		if text == "":
			return "", ""
		if text[0] != "[":
			return "", text
		idx_end = text.find(']') + 1
		return text[:idx_end], text[idx_end:]



	def get_dialogue_at(self, va: str|int):
		print(va)
		if type(va) is str:
			va = int(va,16)
		self.read_string_at_va(va)


	def get_function_info(self, index: int):
		"""
		Retrieves function details by index from the table at `scene_array_va`.
		From entry point to the first jr ra
		We now it works because we used ghidra to determine that each function only has one jr instruction
		
		Returns:
			func_va (int): Virtual address of the function.
			func_name (str): Name of the function.
			func_bytes (bytes): Machine code bytes from start up to and including the delay slot.
		"""
		if not (0 <= index < self.n_functions):
			raise IndexError(f"Index {index} out of range (0 to {self.n_functions - 1}).")

		# Each struct is 12 bytes (4 bytes fn_ptr, 4 bytes name_ptr, 4 bytes unused)
		struct_size = 12
		entry_va = self.scene_array_va + (index * struct_size)
		entry_offset = self.va_to_offset(entry_va)

		# Unpack struct: <IIi = Little-Endian (2x uint32, 1x int32)
		func_va, name_va, _ = struct.unpack('<IIi', self.data[entry_offset : entry_offset + struct_size])

		# Resolve function name string
		func_name = self.read_string_at_va(name_va)

		# Extract function body bytes up to `jr ra` (0x03e00008) + 4-byte delay slot
		func_offset = self.va_to_offset(func_va)
		
		# MIPS instruction for `jr ra` in Little-Endian hex: 08 00 e0 03
		JR_RA_BYTES = b'\x08\x00\xe0\x03'
		
		# Search for `jr ra` starting from the function offset
		jr_ra_index = self.data.find(JR_RA_BYTES, func_offset)
		if jr_ra_index == -1:
			raise ValueError(f"Return statement ('jr ra') not found for function '{func_name}' at {hex(func_va)}")

		# Include the 4-byte `jr ra` AND the following 4-byte delay slot instruction
		func_end = jr_ra_index + 4 + 4
		func_bytes = self.data[func_offset:func_end]

		return func_va, func_name, func_bytes

	def get_all_scenes_info():
		scenes = []
		for i in range(self.n_functions):
			func_va, func_name, func_bytes = self.get_function_info(i)
			info = dict(idx=i, va=func_va, name=func_name, bytes=func_bytes)
			scenes.append(info)

	def read_u32_at_va(self, va: int) -> int:
	    offset = self.va_to_offset(va)

	    if offset + 4 > len(self.data):
	        raise ValueError(
	            f"Cannot read u32 at VA {hex(va)}"
	        )

	    return struct.unpack_from("<I", self.data, offset)[0]

	    
	def read_switch_table(
	    self,
	    table_va: int,
	    first_case: int = -1,
	    last_case: int = 0xE,
	) -> dict[int, int]:

	    cases = {}

	    for case in range(first_case, last_case + 1):
	        index = case - first_case

	        entry_va = table_va + index * 4
	        target_va = self.read_u32_at_va(entry_va)

	        cases[case] = target_va

	    return cases

