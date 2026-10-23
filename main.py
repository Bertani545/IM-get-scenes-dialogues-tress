import gameInformation
import save_scenes_tree
import save_repeating
import json
import sys

# This function does everything

if __name__ == "__main__":
    sys.setrecursionlimit(1500) # I'm tired

    executable_path = "SLPS_255.47"
    gameInfo = gameInformation.GameInfoClass(executable_path)
    gameInfo.extract_all_scenes()

    # Repeating
    raw_repeating = gameInfo.find_repeated_dialogues()
    save_repeating.dump_repeating_dialogues(raw_repeating)
    # Dialogues with awareness of the repeating
    gameInfo.setToUseDefault('repeated.json')
    gameInfo.dump_dialogues("./dialogues")
    
    # Trees
    serializer = save_scenes_tree.SceneTreeInfoClass(executable_path)
    serializer.getSimplifiedTrees()
    serializer.dumpTrees("./trees")