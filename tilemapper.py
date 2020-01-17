#!/usr/bin/python3

import json
from enum import Enum
import math
import sys
import argparse

#Maybe not use fixed 256 here
tileMapWidth = 64

class Entity:
	def __init__(self, entity_type, x_pos, y_pos):
		self.entity_type = int(entity_type)
		self.x_pos = int(x_pos / 16)
		self.y_pos = int(y_pos / 16)

def get_entity_x_pos(elem):
	return elem.x_pos

class Map:
	def __init__(self, mapNumber, jsonData):
		self.map_number = int(mapNumber)
		for prop in jsonData["properties"]:
			if(prop["name"]=="RealHeight"):
				self.height = prop["value"]
			if(prop["name"]=="RealWidth"):
				self.width = prop["value"]
		self.data = jsonData["data"]
		self.entities = {}
		for i in range(int(self.width // 32)):
			self.entities[i] = []
	def addEntities(self, objectData):
		for object in objectData["objects"]:
			type = object["type"]
			x = object["x"]
			y = object["y"]
			newEntity = Entity(type, x, y)
			#The map is divided into sections of entities that are loaded together
			section = int(newEntity.x_pos // 32)
			self.entities[section].append(newEntity)
		#Reorder based on x coordinate
		# print("before:")
		# for entity in self.entities:
		# 	print(entity.x_pos)
		for section in self.entities.keys():
			self.entities[section].sort(key=get_entity_x_pos)
		# print("after:")
		# for entity in self.entities:
		# 	print(entity.x_pos)

tiles = {}
background = []
maplist = {}
nextBank = 1
mapName = ""
tilesetfile = ""

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
	description='Converts a tile map description file to a .inc file to include in assembly.\n\n'
	'Examples:\n\n'
	'tilemapper.py -o tile_map.inc map1.tilemap\n'
	'Read the tilemap map1.tilemap and generate in file tile_map.inc\n\n')
parser.add_argument('input', help='the tilemap input file name')
#parser.add_argument('output', help='the output file name')
args = parser.parse_args()

#READ json file from Tiled
with open(args.input, "r") as read_file:
	data = json.load(read_file)
	#set up maps
	for prop in data["properties"]:
		if(prop["name"]=="MapName"):
			mapName = prop["value"]

	#tilesetfile = "tilemaps/" + data["tilesets"][0]["source"] #TODO loop through props
	tilesetfile = data["tilesets"][0]["source"] #TODO loop through props

	for layer in data["layers"]:
		if(layer["type"] == "tilelayer"):
			maplist[layer["properties"][0]["value"]] = Map(layer["properties"][0]["value"], layer)
	#attach objects
	for layer in data["layers"]:
		if(layer["type"] == "objectgroup"):
			maplist[layer["properties"][0]["value"]].addEntities(layer)


#Write main map index file
with open(mapName + ".inc", "w") as fileOut:
	fileOut.write("!to \"%s.O\", cbm\n*=0\n" % mapName.upper())
	fileOut.write("!byte %s ; %s maps to load\n" % (len(maplist),len(maplist)))
	#Loop through each map layer.  Treating each layer as an individual map
	for i in range(len(maplist.keys())):
		if(i==len(maplist.keys())-1):
			i = -1
		map = maplist[i]
		#fileOut.write("tilemap%d:\n" % i)
		heightValue = 0
		if(map.height == 64):
			heightValue = 1
		elif(map.height == 128):
			heightValue = 2
		elif(map.height == 256):
			heightValue = 3
		widthValue = 0
		if(map.width == 64):
			widthValue = 1
		elif(map.width == 128):
			widthValue = 2
		elif(map.width == 256):
			widthValue = 3

		fileOut.write("!byte %s\n" % widthValue) #TODO make sure game accounts for both -1s
		fileOut.write("!byte %s\n" % heightValue)
		mapsize = map.width * map.height * 2
		banks =  math.ceil(mapsize / 8192)
		banks = banks + 1 # account for entity bank
		fileOut.write("!byte %s\n" % nextBank)
		nextBank += banks
		mapfilename = mapfilename = (mapName+ str(map.map_number) + ".o")
		if(i == -1):
			mapfilename = mapName + "bg.o"
		fileOut.write("!byte %s\n" % len(mapfilename))
		fileOut.write("!pet \"%s\"\n" % mapfilename.lower())

		#Write individual map file
		with open(mapfilename + ".asm", "w") as fileOutMap:
			#fileOutMap.write("!to \"%s\", cbm\n*=0\n" % mapfilename.upper())
			#fileOutMap.write("!byte $FF\n")
			entities = map.entities
			#Write each section of entities in the the map to a different
			# page of memory
#			for section in entities.keys():
#				start_address = 0x0100 *(section+1)
#				fileOutMap.write("*=$%s\n" % hex(start_address).lstrip("0x"))

#				for entity in entities[section]:
#					fileOutMap.write("!byte $%s," % hex(entity.x_pos).lstrip("0x"))
#					fileOutMap.write(" $%s," % hex(entity.y_pos).lstrip("0x"))
#					fileOutMap.write(" $%s," % hex(entity.entity_type).lstrip("0x"))
#					fileOutMap.write(" $00\n") #unused for now

				#fill the rest of page with 0
#				fill_amount = 256-(4*len(entities[section]))
#				fileOutMap.write("!fill $%s\n" % hex(fill_amount).lstrip("0x"))

			#The tilemap data starts at address $2000
			fileOutMap.write("*=$4000\ntestbg_map:\n")

			#print("Map W&H: ", tileMapWidth, "x", tileMapHeight);
			for y in range(map.height):
				fileOutMap.write("\t!byte ")
				for x in range(map.width):
					tileIndex = y * tileMapWidth + x
					tileValue = map.data[tileIndex] - 1
					lowByte = tileValue & 0xFF
					fileOutMap.write("%d, " % lowByte)
					#do second byte palette offset and highest part of tile number
					tileNumberHighByte = (tileValue >> 8) & 0x03
					tileFlippedHorizontally = ((tileValue & 0x80000000) != 0)
					tileFlippedVertically = ((tileValue & 0x40000000) != 0)
					#tileFlippedDiagonally = ((tileValue & 0x20000000) != 0) #should not be used #TODO maybe add warning
					paletteoffsetByte = 0 << 4
					flipbyte = (int(tileFlippedHorizontally) << 2) | (int(tileFlippedVertically) << 3)
					highByte = tileNumberHighByte | paletteoffsetByte | flipbyte

					if(x==map.width-1):
						fileOutMap.write("%d" % highByte)
					else:
						fileOutMap.write("%d, " % highByte)
				fileOutMap.write("\n")

with open(tilesetfile, "r") as tileset_file:
	data = json.load(tileset_file)
	varsfilename = mapName + "vars.asm"
	varsassembledfilename = (mapName + "vars.o").upper()
	with open(varsfilename,"w") as fileOut:
		fileOut.write("!to \"%s\", cbm\n*=0\n" % varsassembledfilename)
		tiles = data["tiles"]
		for tile in tiles:
			type = int(tile["type"])
			fileOut.write("!byte %d\n" %type)
