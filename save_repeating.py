import gameInformation
import json
# source .decompile/bin/activate
# --- Usage Example ---

def build_repeated_dialogues(repeated):

    result = {}

    for text_address, occurrences in repeated.items():
        try:
            result[f"0x{text_address:08X}"] = {
                "original": occurrences[0]["original"],
                "metadata": occurrences[0]["metadata"],
                "en": "",
                "es": "",

            }
        except:
            json.dumps(occurrences)

    return result


def dump_repeating_dialogues(raw_repeating):
    json_struct = build_repeated_dialogues(raw_repeating)
    with open("repeated.json", "w") as f:
            json.dump(
                json_struct,
                f,
                ensure_ascii=False,
                indent=4
            )


if __name__ == "__main__":
    # 1. Load the executable
    executable_path = "SLPS_255.47"
    gameInfo = gameInformation.GameInfoClass(executable_path)
    gameInfo.extract_all_scenes()
    raw_repeating = gameInfo.find_repeated_dialogues()
    json_struct = build_repeated_dialogues(raw_repeating)
    #analyzer = gameInfo.getSceneAnalyzer(127)
    #analyzer.analyze()
    #all_scenes = analyzer.extract_scene_dialogues()
    with open("repeated.json", "w") as f:
            json.dump(
                json_struct,
                f,
                ensure_ascii=False,
                indent=4
            )