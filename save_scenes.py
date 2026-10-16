import gameInformation
import json
# source .decompile/bin/activate
# --- Usage Example ---

if __name__ == "__main__":
    # 1. Load the executable
    executable_path = "SLPS_255.47"
    gameInfo = gameInformation.GameInfoClass(executable_path)
    gameInfo.extract_all_scenes()
    gameInfo.setToUseDefault('repeated.json')
    gameInfo.dump_dialogues("dialogues")





