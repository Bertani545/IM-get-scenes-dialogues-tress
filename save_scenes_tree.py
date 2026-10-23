from dataclasses import dataclass, field
import controlFlow
import retrieve_function_bytes
import decodeFunction
import constants
from collections import defaultdict
from pathlib import Path
import json
import os
import sys

@dataclass
class SceneTreeInfoClass:

	def __init__(
		self,
		executable_path: str
	):
		self.wrapper = retrieve_function_bytes.SceneFunctionsWrapper(executable_path)
		self.decoder = decodeFunction.MIPSDecoder()
		self.trees = None

	def __del__(self):
		pass

	def get_scene_tree(self, analyzer):
		nodes, edges = self.serialize_tree(analyzer)
		return {
			"scene": analyzer.number,
			"name": analyzer.function_name,
			"nodes": nodes,
			"edges": edges
		}


	def getSceneAnalyzer(self, function_id):
		func_va, func_name, func_bytes = self.wrapper.get_function_info(function_id)
		instructions = self.decoder.decode(
			func_bytes,
			func_va,
			constants.function_registers
		)
		return controlFlow.ControlFlowAnalyzer(func_va, func_name, function_id, instructions, self.wrapper)

	def parseNode(self, key, node):
		return { "id": key, "type": node["type"] }

	def parseEdge(self, parent_key, child_key):
		return {
			"id": f"{parent_key}-{child_key}",
			"souce": parent_key,
			"target": child_key
		}


	def serialize_tree(self, analyzer):
		root = analyzer.analyze()
		root, _ = analyzer.build_branch_graph(root)

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

	def getSimplifiedTrees(self):
		trees = []
		for scene_id in range(self.wrapper.n_effective_function):
			analyzer = self.getSceneAnalyzer(scene_id)
			print(
                f"Extracting scene {scene_id} at {hex(analyzer.function_va)}: "
                f"{analyzer.function_name}"
            )
			tree = self.get_scene_tree(analyzer)
			trees.append(tree)
		self.trees = trees

	def dumpTrees(self, output_dir):
		for tree in self.trees:
			self.saveTree(tree, output_dir)


	def saveTree(self, tree_data, output_dir):
		output_dir = Path(output_dir)

		output_dir.mkdir(parents=True, exist_ok=True)

		path = output_dir / f"tree_{tree_data['scene']:03d}.json"

		with path.open("w", encoding="utf-8") as f:
			json.dump(
				tree_data,
				f,
				ensure_ascii=False,
				indent=4
			)


if __name__ == '__main__':

	sys.setrecursionlimit(1500) # I'm tired
	serializer = SceneTreeInfoClass('./SLPS_255.47')
	serializer.getSimplifiedTrees()
	serializer.dumpTrees("./trees")
