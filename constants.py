class UnknownValue:
    def __repr__(self):
        return "UNKNOWN"

    def __str__(self):
        return "UNKNOWN"

UNKNOWN = UnknownValue()

VA_OFFSET = 0xFFF80

# Virtual Addresses of these functions
interesting_jals = {
	0x133700, #Black dialogue
    0x133ad0, #MC
    0x133910, #Girls
    0x133780, #Girls2
    0x1335b0, #Option selector (for 3)
    #0x1334c0, # Option selector (4) should not be touched
    #0x12f970, #Displays items description (This one should not be touched)
}

def check_if_important_jal(ins_str):
    try:
        val = int(ins_str,16)
        return val in function_registers
    except:
        return False

def check_if_important_jal_int(val):
    return val in function_registers

function_registers = {
    0x133700: { #Black dialogue
            "registers": ["a0", "a1"],
            "dialogue": ["a0"],
            "type": "black"
        }, 
    0x133ad0: {#MC
            "registers": ["a0"], 
            "dialogue": ["a0"],
            "type": "regular"
        },
    0x133910: {#Girls
            "registers": ["a0", "a1", "a2"],
            "dialogue": ["a0"],
            "type": "regular"
        },
    0x133780: { #Girls2
            "registers": ["a0", "a1", "a2"],
            "dialogue": ["a0"],
            "type": "regular"
        },
    0x1335b0: { #Option selector (for 3)
            "registers": ["a0", "a1", "a2", "a3"], 
            "dialogue": ["a0", "a1", "a2"],
            "type": "selector"
        },
    
    #0x12f970, #Displays items description (This one should not be touched now)

    0x1334c0: {
        "registers": ["a0", "a1", "a2", "a3"], 
        "dialogue": ["a0", "a1", "a2", "a3"],
        "type": "selector"
    }, # Option selector (4) Especial case that I prefer doing later because it works different
}


'''
interesting_jals = {
	0xc0cd040c, #Black dialogue
    0xb4ce040c, #MC
    0x44ce040c, #Girls
    0xe0cd040c, #Girls2
    0x6ccd040c, #Option selector (for 3)
    0x30cd040c, # Option selector (4) should not be touched
    0x5cbe040c, #Displays items description (This one should not be touched)
}
'''

# The items descriptions start at VA = 309900. These are pointers too
# The letters start at VA = 309960. But they are only ptrs so we can modify them
# las cosas con precios deberán ser parchadas encima

