from dataclasses import dataclass, field
import controlFlow
import retrieve_function_bytes
import decodeFunction
import constants
from collections import defaultdict
from pathlib import Path
import json
import os

@dataclass
class SceneTreeSerializer:

	def __init__(
		self,
		executable_path: str,
		dialogue_jsons_path: str,
		repeated_path: str
	):
		self.wrapper = retrieve_function_bytes.SceneFunctionsWrapper(executable_path)
		self.decoder = decodeFunction.MIPSDecoder()
		self.jsons_path = dialogue_jsons_path
		self.repeating_dialogues = None
		self.get_repeating(repeated_path)
		self.analyzer = None
		self.scene_json = None

	def __del__(self):
		pass

	def get_scene_tree(self, scene_id):
		self.getSceneAnalyzer(scene_id)
		self.load_json(scene_id)
		return self.serialize_tree()


	def getSceneAnalyzer(self, function_id):
		func_va, func_name, func_bytes = self.wrapper.get_function_info(function_id)
		instructions = self.decoder.decode(
			func_bytes,
			func_va,
			constants.interesting_jals
		)
		self.analyzer = controlFlow.ControlFlowAnalyzer(func_va, func_name, function_id, instructions, self.wrapper)

		#extract_dialogue_from_call from controlFlow works pretty similar

	def load_json(self, function_id):
		file_name = f"scene_{function_id:03}.json"
		path  = os.path.join(self.jsons_path, file_name)
		with open(path) as f:
			self.scene_json = json.load(f)

	def get_repeating(self, json_path):
		file_name = "repeated.json"
		path  = os.path.join(json_path, file_name)
		with open(path) as f:
			self.repeating_dialogues = json.load(f)

	def parseNode(self, key, node):

		# Default for better reading
		if node["type"] != "dialogue":
			return { "id": key, "type": node["type"] }

		call_address = node["data"]
		call_hex = f'0x{call_address:08X}'

		json_dialogues = self.scene_json["calls"][call_hex]["dialogues"]
		function_address = self.scene_json["calls"][call_hex]["function_address"]

		node_dict = {
			"id": key,
			"type": "dialogue",
			"function": f'0x{function_address:08X}'
		}

		dialogues = []
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
		node_dict["dialogues"] = dialogues
		return node_dict



	def parseEdge(self, parent_key, child_key):
		return {
			"id": f"{parent_key}-{child_key}",
			"souce": parent_key,
			"target": child_key
		}


	def serialize_tree(self):
		root = self.analyzer.analyze()
		root, _ = self.analyzer.build_branch_graph(root)

		visited = set()
		edges = []
		nodes = {}

		def visit(node, parent_key = None):

			key = f"0x{node["id"]:08X}"

			if parent_key is not None:
				edges.append(self.parseEdge(parent_key, key))

			
			if key in visited:
				#print(f"[already visited]")
				return

			visited.add(key)

			parsedNode = self.parseNode(key, node)

			nodes[key] = parsedNode

			for child in node["children"]:
				visit(child, key)

		visit(root)

		return nodes, edges


if __name__ == '__main__':
	import sys
	try:
		scene_n = int(sys.argv[1:][0])
	except:
		print("Couldn't obtain the scene number")
		sys.exit()
	serializer = SceneTreeSerializer('./SLPS_255.47', "./dialogues", "./")
	nodes, edges = serializer.get_scene_tree(scene_n)

	final_struct = {
		"nodes": nodes,
		"edges": edges
	}

	print(json.dumps(final_struct, indent=4, ensure_ascii=False))
	'''
	for node in nodes:
		print(node)
		print(json.dumps(nodes[node], indent=4, ensure_ascii=False))
		print()


	for e in edges:
		print(e)
	'''






# prubas con 520