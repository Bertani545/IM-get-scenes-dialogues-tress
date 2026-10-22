import json
import os

class SceneTreeSerializer:

	def __init__(
		self,
		dialogue_jsons_path: str,
		tree_jsons_path: str,
		repeated_path: str
	):
		self.dialogues_path = dialogue_jsons_path
		self.trees_path  = tree_jsons_path
		self.repeating_dialogues = None
		self.get_repeating(repeated_path)

	def __del__(self):
		pass

	def get_repeating(self, json_path):
		file_name = "repeated.json"
		path  = os.path.join(json_path, file_name)
		with open(path) as f:
			self.repeating_dialogues = json.load(f)

	def load_scene_dialogues(self, id_scene):
		file_name = f"scene_{id_scene:03}.json"
		path  = os.path.join(self.dialogues_path, file_name)
		scene_json = None
		with open(path) as f:
			scene_json = json.load(f)
		return scene_json

	def load_scene_tree(self, id_scene):
		file_name = f"tree_{id_scene:03}.json"
		path  = os.path.join(self.trees_path, file_name)
		tree_json = None
		with open(path) as f:
			tree_json = json.load(f)
		return tree_json

	def get_scene_tree(self, scene_id):
		dialogues_json = self.load_scene_dialogues(scene_id)
		tree_json = self.load_scene_tree(scene_id)
		return self.serialize_tree(dialogues_json, tree_json)

	def parseNode(self, node, calls):

		# Default for better reading
		if node["type"] != "dialogue":
			return node


		call = calls[node["id"]]
		dialogues = []
		json_dialogues = call["dialogues"]
		for register in json_dialogues:
			dialogue_info = json_dialogues[register]
			text_address = f"0x{dialogue_info["text_address"]:08X}"
			en = None
			es = None
			if dialogue_info["use_default"]:
				info = self.repeating_dialogues[text_address]
				en = info["en"]
				es = info["es"]
			else:
				en = dialogue_info["en"]
				es = dialogue_info["es"]

			dialogues.append({
				"register": register,
				"text_address": text_address,
				"original": dialogue_info["original"],
				"metadata": dialogue_info["metadata"],
				"en": en,
				"es": es,
				"use_default": dialogue_info["use_default"]
			})

		parsed_node = {
			"id": node["id"],
			"type": "dialogue",
			"function": f"0x{call["function_address"]:08X}",
			"dialogues": dialogues
		}
		return parsed_node


	def serialize_tree(self, dialogues_json, tree_json):
		tree_nodes = tree_json["nodes"]
		tree_edges = tree_json["edges"]
		calls = dialogues_json["calls"]

		nodes = []
		for node_id in tree_nodes:
			nodes.append(self.parseNode(tree_nodes[node_id], calls))

		serialized_tree = {
			"scene": dialogues_json["scene"],
    		"name": dialogues_json["name"],
			"nodes": nodes,
    		"edges": tree_edges 
		}
		return serialized_tree
		

if __name__ == '__main__':
	import sys
	try:
		scene_n = int(sys.argv[1:][0])
	except:
		print("Couldn't obtain the scene number")
		sys.exit()
	serializer = SceneTreeSerializer("./dialogues", "./trees", "./")
	final_struct = serializer.get_scene_tree(scene_n)

	print(json.dumps(final_struct, indent=4, ensure_ascii=False))






# prubas con 520