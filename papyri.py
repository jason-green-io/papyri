import sys
import minecraftmap
import yaml
import os
import glob
import PIL
import pyvips
import shutil
import io
import requests
from nbt.nbt import NBTFile, TAG_Long, TAG_Int, TAG_String, TAG_List, TAG_Compound
import re
import collections
import argparse


parser = argparse.ArgumentParser(description='convert minecraft maps to the web')
parser.add_argument('--poi', action='store_true', help="generate POI")
parser.add_argument('--mcdata', help="input path to minecraft server data")
parser.add_argument('--output', help="output path for web stuff")
parser.add_argument("--size", help="size of map to render, centered on 0,0", type=int, default=2000)

args = parser.parse_args()
print(args)





mcdata = args.mcdata
papyriOutputPath = args.output

# This is the font used for the POI index number
fontpath = os.path.join("04B_03B_.TTF")

# Format for the structure of a link pointing to a specific location on the map 
linkFormat = "map/#dim/overworld/{}/{}/184.0000"

# regular expression searching for coordinates
poiRE = "(.*)\n(-?\d+), ?(-?\d+)\n(.*)"

# regular expression searching for HTML 8bit color codes
colorRE = "(#[0-9a-fA-F]{6})"

# This is the header of the generated .md file
fileHeader = """
# Papyri

### Maps

These maps are generated using the maps created in game.

[Overworld](map/#dim/overworld)
[Nether](map/#dim/nether)
[End](map/#dim/end)


### Instructions for POI

To start, name a book starting with the word `papyri` and place it in your inventory or ender chest. Create points of interest (POI) in this format:

    Title
    coordinates
    Decription
    
Organize your POI using tags. Tags are any words surrounded by `[]`. Example: `[base]` Use HTML colors in the description to change the POI color. Example: `#009900`. 

"""

# Header for the tag tables in markdown
tableHeader ="""
| |
|:-|
"""

# row format for each POI in markdown
poiFormat = "|![]({0}{6}.png) **{1}**<br>[{2}, {3}]({4})<br>{5}|\n"

poiMd = ""

# location of the palyer data files
playerDatFilesPath = os.path.join(mcdata, "playerdata", "*.dat")

# list of all the player data files
playerDatFiles = glob.glob(playerDatFilesPath)

# empty defaultdict for all the tags
taggedPois = collections.defaultdict(list)

# scale factor
scaleFactor = 1

# this is how much of the map is rendered
canvasSize = args.size * scaleFactor

def unpack_nbt(tag):
    """                                                                                                                                                                                                            
    Unpack an NBT tag into a native Python data structure.                                                                                                                                                         
    """

    if isinstance(tag, TAG_List):
        return [unpack_nbt(i) for i in tag.tags]
    elif isinstance(tag, TAG_Compound):
        return dict((i.name, unpack_nbt(i)) for i in tag.tags)
    else:
        return tag.value


# counter for generating the POI indexes
UUIDCounter = collections.Counter()


for datFile in playerDatFiles:
    nbtObject = NBTFile(datFile)
    nbtDict = unpack_nbt(nbtObject)
    inventory = nbtDict.get("Inventory", {})
    enderChest = nbtDict.get("EnderItems", {})
    books = [b for b in inventory if b["id"] == "minecraft:writable_book"] + [b for b in enderChest if b["id"] == "minecraft:writable_book"]
    for book in books:
    
        if book.get("tag", {}).get("display", {}).get("Name", "").lower().startswith("papyri"):
            for page in book.get("tag",{}).get("pages", []):
                for each in  re.findall(poiRE, page):
                    title, x, z, desc = each
        
                    desc = desc.replace("\n", " ")
                    tags = re.findall("\[(.*?)\]", desc)
                    colors = re.findall(colorRE, desc)
                    
                    desc = re.subn("\[(.*?)\]", r"[\1](http://minecraft.greener.ca/#!papyri.md#\1)", desc)[0]
                    
                    # print(repr(desc))
                    x = int(x)
                    z = int(z)
                    viewerx = (x * scaleFactor + canvasSize / 2) / canvasSize
                    viewerz = (z * scaleFactor + canvasSize / 2) / canvasSize
                    uuid = datFile.split("/")[-1].split(".")[0]
                    UUIDCounter.update([uuid])
                    num = UUIDCounter[uuid]
                    if colors:
                        color = colors
                    else:
                        color = ["black"]
                    if tags:
                        
                        for tag in tags:
                            taggedPois[tag].append((uuid, title, x,z, linkFormat.format(viewerx,viewerz), desc, num, color))
                    else:
                        taggedPois["untagged"].append((uuid, title,x,z, linkFormat.format(viewerx,viewerz), desc, num, color))
                        #poisFile.write("|![]({})|[{}, {}]({})|{}|{}|\n".format(head, x,z, linkFormat.format(viewerx,viewerz), title, desc))



if not os.path.exists(papyriOutputPath):
    os.makedirs(papyriOutputPath)
    os.makedirs(os.path.join(papyriOutputPath, "map"))
    
    shutil.copy(os.path.join("template", "index.html"), papyriOutputPath)
    shutil.copy(os.path.join("template", "map", "index.html"), os.path.join(papyriOutputPath, "map"))
    shutil.copy(os.path.join("template", "map", "script.js"), os.path.join(papyriOutputPath, "map"))
    shutil.copy(os.path.join("template", "map", "style.css"), os.path.join(papyriOutputPath, "map"))
    
    
with open(os.path.join(papyriOutputPath, "index.md"), "w", encoding="utf-8") as poisFile:
    poisFile.write(fileHeader)
    for tag in sorted(taggedPois):
        poisFile.write("## {}".format(tag))
        poisFile.write(tableHeader)
        for poi in taggedPois[tag]:
            poisFile.write(poiFormat.format(*poi))

        


mapsInputGlob = os.path.join(mcdata, "data", "map*.dat")

dimDict = {-1: "nether", 0: "overworld", 1: "end"}

mapFiles = glob.glob(mapsInputGlob)
#print(mapFiles)
mapFiles.sort(key=os.path.getmtime)

background = {d: PIL.Image.new('RGBA', (canvasSize, canvasSize), (0, 0, 0, 255)) for d in dimDict}
bg = {d: pyvips.Image.black(canvasSize, canvasSize) for d in dimDict}

mapFileObjs = []
for mapFile in mapFiles:
    print(mapFile)
    mapFileObjs.append(minecraftmap.Map(mapFile,eco=False))
mapFileObjs.sort(key=lambda m: m.zoomlevel, reverse=True)

for m in mapFileObjs:
    print(m.centerxz, m.dimension, m.zoomlevel)
    dimension = m.dimension
    zoom = str(m.zoomlevel)
    x = int((m.centerxz[0] * scaleFactor ) + canvasSize / 2 - 128 * 2 ** m.zoomlevel / 2 * scaleFactor)
    z = int((m.centerxz[1] * scaleFactor ) + canvasSize / 2 - 128 * 2 ** m.zoomlevel / 2 * scaleFactor)
    # coords = ".".join([str(a - canvasSize / 2) for a in m.centerxz] + [dimension])
    m.genimage()
    m.rescale(num=scaleFactor)

    #memory_area = io.BytesIO()
    #m.im.save(memory_area,'PNG')
    #image_str = memory_area.getvalue()
    #im_mask_from_memory = pyvips.Image.new_from_buffer(image_str, "")

    background[dimension].paste(m.im, (x, z), m.im)
    #bg[dimension].insert(im_mask_from_memory, x, z)
    
    # m.saveimagepng(os.path.join(webdata, "newmap", imageFile))
    



    #img = Image.open('/pathto/file', 'r')
    
    #img_w, img_h = img.size
    
    #bg_w, bg_h = background.size
    #offset = ((bg_w - img_w) / 2, (bg_h - img_h) / 2)




for tag in sorted(taggedPois):
    for poi in taggedPois[tag]:
        response = requests.get("https://crafatar.com/avatars/{}?size=8".format(poi[0]))

        imgTest = PIL.Image.new("RGBA", (24, 12), "black")

        draw = PIL.ImageDraw.Draw(imgTest)
        totalColors = len(poi[7])
        rectHeight = 12 // totalColors
        for each in enumerate(poi[7]):
            
            point1 = (0, rectHeight * each[0])
            point2 = (11, rectHeight * each[0] + rectHeight)
            draw.rectangle([point1, point2], fill=each[1])
        draw.text((14, 2), str(poi[6]), font=PIL.ImageFont.truetype(fontpath,8))
        imgTest.paste(PIL.Image.open(io.BytesIO(response.content)), (2, 2))
        #mask = imgTest.convert("L").point(lambda x: min(x, 100))
        #imgAlpha = imgTest
        #imgAlpha.putalpha(mask)
        #imgBorder = PIL.Image.new("RGBA", (26, 10), "black")
        #imgBorder.paste(imgTest, (1,1))
        background[0].paste(imgTest, (poi[2] * scaleFactor + canvasSize // 2 - 12, poi[3] * scaleFactor + canvasSize // 2 - 4))
        imgOut = imgTest.resize((48, 24))
        imgOut.save(os.path.join(papyriOutputPath, poi[0] + str(poi[6]) + ".png"), "png")

for d in dimDict:
    mapOutputPath = os.path.join(papyriOutputPath, "map", "dim", dimDict[d])
    if not os.path.exists(mapOutputPath):
        os.makedirs(mapOutputPath)


        
for d in dimDict:
    mapOutputPath = os.path.join(papyriOutputPath, "map", "dim", dimDict[d])
    outPngFile = os.path.join(mapOutputPath, 'out{}.png'.format(d))

    background[d].save(outPngFile)
    outputDir = os.path.join(mapOutputPath, '{}_files'.format(dimDict[d]))
    dz = pyvips.Image.new_from_file(outPngFile, access='sequential')
    if os.path.exists(outputDir):
        shutil.rmtree(outputDir)
    dz.dzsave(os.path.join(mapOutputPath, '{}'.format(dimDict[d])), suffix=".png")
    #bg[d].dzsave(os.path.join(webdata, "newmap", 'out{}'.format(d)), suffix=".png")

    
#bg.write_to_file("test.png")
