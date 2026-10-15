from dataclasses import dataclass, field
import controlFlow
import retrieve_function_bytes
import decodeFunction
import constants
from collections import defaultdict
from pathlib import Path
import json
import datetime



@dataclass
class GameInfoClass:

    def __init__(
        self,
        executable_path: str
    ):
        self.wrapper = retrieve_function_bytes.SceneFunctionsWrapper(executable_path)
        self.decoder = decodeFunction.MIPSDecoder()
        self.scenes = None

    
    def getSceneAnalyzer(self, function_id):
        func_va, func_name, func_bytes = self.wrapper.get_function_info(function_id)
        instructions = self.decoder.decode(
            func_bytes,
            func_va,
            constants.interesting_jals
        )
        return controlFlow.ControlFlowAnalyzer(func_va, func_name, function_id, instructions, self.wrapper)

    def extract_all_scenes(self):
        scenes = []
        for idx in range(self.wrapper.n_effective_function):
            analyzer = self.getSceneAnalyzer(idx)
            print(
                f"Extracting scene {analyzer.number} at {hex(analyzer.function_va)}: "
                f"{analyzer.function_name}"
            )
            scene_data = analyzer.extract_scene() # One analizer per scene
            scenes.append(scene_data)

        self.scenes = scenes
        return scenes

    def get_dialogue_occurrences(self):
        occurrences = []

        for scene in self.scenes:
            calls = scene["calls"]
            for call in calls:
                call_info = calls[call]
                dialogues = call_info["dialogues"]
                for dialogue in dialogues:
                    info = dialogues[dialogue]
                    occurrences.append({
                        "text_address": info["text_address"],
                        "original": info["original"],
                        "metadata": info["metadata"],
                        "scene": scene["scene"],
                        "scene_name": scene["name"],
                        "call_address": call_info["call_address"],
                        "function_address": call_info["function_address"],
                        "register": info["register"],
                    })

        return occurrences

    def find_repeated_dialogues(self):
        occurrences = self.get_dialogue_occurrences()

        grouped = defaultdict(list)

        for occurrence in occurrences:
            grouped[occurrence["text_address"]].append(occurrence)

        repeated = {
            address: items
            for address, items in grouped.items()
            if len(items) >= 2
        }

        return repeated

    def dump_dialogues(self, output_dir):
        for scene in self.scenes:
            scene["last_edit"] = {"user": "bertani", "time": str(datetime.datetime.now())}
            self.save_scene(scene, output_dir)


    def save_scene(self, scene_data, output_dir):
        output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        path = output_dir / f"scene_{scene_data['scene']:03d}.json"

        with path.open("w", encoding="utf-8") as f:
            json.dump(
                scene_data,
                f,
                ensure_ascii=False,
                indent=4,
                default=json_default
            )

    
def json_default(obj):
  if isinstance(obj, constants.UnknownValue):
    return str(obj)  # or simply return "UNKNOWN"
  raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")