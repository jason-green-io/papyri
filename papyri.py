#!/usr/bin/env python3
import sys
import minecraftmap
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
import logging


# setup the parser for command line options
parser = argparse.ArgumentParser(description='convert minecraft maps to the web')
parser.add_argument('--poi', action='store_true', help="generate POI")
parser.add_argument('--mcdata', help="input path to minecraft server data", required=True)
parser.add_argument('--output', help="output path for web stuff", required=True)
parser.add_argument("--size", help="size in blocks of map to render, centered on 0,0, default is 2000", type=int, default=2000)

# Setup the logger
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)


# get the args
args = parser.parse_args()
logging.info(args)


# Set the input minecraft world folder
mcdata = args.mcdata

# Set the output web stuff folder
papyriOutputPath = args.output

# This is the font used for the POI index number
fontpath = os.path.join("04B_03B_.TTF")

# scale factor
scaleFactor = 1

# viewer zoom level
viewerZoom = args.size * 0.0092

# this is how much of the map is rendered
canvasSize = args.size * scaleFactor

# Format for the structure of a link pointing to a specific location on the map 
linkFormat = "map/#dim/overworld/{}/{}/" + str(viewerZoom)

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
    -1234, 567
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

logging.info("Found %s player(s)", len(playerDatFiles))

# empty defaultdict for all the tags
taggedPois = collections.defaultdict(list)


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


# iterate over all the player dat files
for datFile in playerDatFiles:
    # create python object from the dat file
    nbtObject = NBTFile(datFile)   
    nbtDict = unpack_nbt(nbtObject)

    # get the inventory and enderchest items
    inventory = nbtDict.get("Inventory", {})
    enderChest = nbtDict.get("EnderItems", {})

    # get all the books in there
    books = [b for b in inventory if b["id"] == "minecraft:writable_book"] + [b for b in enderChest if b["id"] == "minecraft:writable_book"]

    # iterate over the books
    for book in books:

        # check if the book starts with "papyri"
        bookName = book.get("tag", {}).get("display", {}).get("Name", "")
                    
        if "papyri" in bookName:

            # iterate over the pages
            for page in book.get("tag",{}).get("pages", []):

                #iterate over every POI found on a page
                for each in  re.findall(poiRE, page):

                    # get the stuff from the POI
                    title, x, z, desc = each

                    # get rid of newlines in the description
                    desc = desc.replace("\n", " ")

                    # find all the tags
                    tags = re.findall("\[(.*?)\]", desc)

                    # find all the colors
                    colors = re.findall(colorRE, desc)

                    # replace the tags with markdown links to the tag categories
                    desc = re.subn("\[(.*?)\]", r"[\1](#\1)", desc)[0]
                    
                    # print(repr(desc))

                    # convert the coordinates of the POI to osd viewer coordinates
                    x = int(x)
                    z = int(z)
                    viewerx = (x * scaleFactor + canvasSize / 2) / canvasSize
                    viewerz = (z * scaleFactor + canvasSize / 2) / canvasSize

                    # get the uuid of the player who has this book
                    uuid = datFile.split("/")[-1].split(".")[0]

                    # increment the counter keeping track of POI per player
                    UUIDCounter.update([uuid])

                    # get the current count to use as a POI id
                    num = UUIDCounter[uuid]

                    # if there's colors, get them, otherwise, default to black
                    if colors:
                        color = colors
                    else:
                        color = ["black"]

                    # prepare a POI for writing
                    POI = (uuid, title, x,z, linkFormat.format(viewerx,viewerz), desc, num, color)

                    logging.info(POI)
                    
                    # if there's tags, append to the tag dict, otherwise, add to dict as untagged
                    if tags:
                        
                        for tag in tags:
                            taggedPois[tag].append(POI)
                    else:
                        taggedPois["untagged"].append(POI)
                    

logging.info("Created %s tags", len(taggedPois))

# create the output folders if they don't exsist
if not os.path.exists(papyriOutputPath):
    logging.info("Creating output folders")
    os.makedirs(papyriOutputPath)
    os.makedirs(os.path.join(papyriOutputPath, "map"))

    # copy the web template files to the output folders
    logging.info("Copying template web files")
    shutil.copy(os.path.join("template", "index.html"), papyriOutputPath)
    shutil.copy(os.path.join("template", "map", "index.html"), os.path.join(papyriOutputPath, "map"))
    shutil.copy(os.path.join("template", "map", "script.js"), os.path.join(papyriOutputPath, "map"))
    shutil.copy(os.path.join("template", "map", "style.css"), os.path.join(papyriOutputPath, "map"))
    
logging.info("Writing index.md containg POI")

# write the index.md file containing all the POI
with open(os.path.join(papyriOutputPath, "index.md"), "w", encoding="utf-8") as poisFile:

    # write the header
    poisFile.write(fileHeader)

    # iterate over each tag
    for tag in sorted(taggedPois):
        #write the header for the tag
        poisFile.write("## {}".format(tag))
        poisFile.write(tableHeader)

        # iterate over all the POI in the tag
        for poi in taggedPois[tag]:
            poisFile.write(poiFormat.format(*poi))

        

# path to maps
mapsInputGlob = os.path.join(mcdata, "data", "map*.dat")

# dimesnion value to anme dict
dimDict = {-1: "nether", 0: "overworld", 1: "end"}

# get all the maps
mapFiles = glob.glob(mapsInputGlob)

# sort the maps by modified time
mapFiles.sort(key=os.path.getmtime)

logging.info("Found %s maps", len(mapFiles))

# create the output map images, one per dimension
background = {d: PIL.Image.new('RGBA', (canvasSize, canvasSize), (0, 0, 0, 255)) for d in dimDict}
#bg = {d: pyvips.Image.black(canvasSize, canvasSize) for d in dimDict}

# create a list for the map objects
mapFileObjs = []

logging.info("Parsing map .dat files")

# get all the map objects
for mapFile in mapFiles:
    mapFileObjs.append(minecraftmap.Map(mapFile,eco=False))

# sort them by zoom level
mapFileObjs.sort(key=lambda m: m.zoomlevel, reverse=True)

# iterate over all the map objects
for m in mapFileObjs:
    dimension = m.dimension
    zoom = str(m.zoomlevel)
    x = int((m.centerxz[0] * scaleFactor ) + canvasSize / 2 - 128 * 2 ** m.zoomlevel / 2 * scaleFactor)
    z = int((m.centerxz[1] * scaleFactor ) + canvasSize / 2 - 128 * 2 ** m.zoomlevel / 2 * scaleFactor)


    logging.info("Stitching map at %s, %s zoom level %s in %s", x, z, zoom, dimDict[dimension])

    # create an image from the .dat data
    m.genimage()

    # rescale the image base on the zoom level
    m.rescale(num=scaleFactor)

    #memory_area = io.BytesIO()
    #m.im.save(memory_area,'PNG')
    #image_str = memory_area.getvalue()
    #im_mask_from_memory = pyvips.Image.new_from_buffer(image_str, "")

    # add the image to the appropriate output map
    background[dimension].paste(m.im, (x, z), m.im)
    #bg[dimension].insert(im_mask_from_memory, x, z)
    
    # m.saveimagepng(os.path.join(webdata, "newmap", imageFile))
    #img = Image.open('/pathto/file', 'r')
    #img_w, img_h = img.size
    #bg_w, bg_h = background.size
    #offset = ((bg_w - img_w) / 2, (bg_h - img_h) / 2)



logging.info("Adding POI to stiched map")

# iterate over the tags to add POI to map
for tag in sorted(taggedPois):
    # iterate over POI in tag
    for poi in taggedPois[tag]:
        
        # get POI player head 
        response = requests.get("https://crafatar.com/avatars/{}?size=8".format(poi[0]))

        #create a new base POI
        imgTest = PIL.Image.new("RGBA", (24, 12), "black")

        # object to draw on base POI
        draw = PIL.ImageDraw.Draw(imgTest)

        # get the number of colors in POI
        totalColors = len(poi[7])

        # calculate how high a color bar will be 
        rectHeight = 12 // totalColors

        # iterate over each color
        for each in enumerate(poi[7]):
            # draw a color bar on base POI
            point1 = (0, rectHeight * each[0])
            point2 = (11, rectHeight * each[0] + rectHeight)
            draw.rectangle([point1, point2], fill=each[1])
            
        # add the POI id as a number
        draw.text((14, 2), str(poi[6]), font=PIL.ImageFont.truetype(fontpath,8))

        # add the player head
        imgTest.paste(PIL.Image.open(io.BytesIO(response.content)), (2, 2))
        
        #mask = imgTest.convert("L").point(lambda x: min(x, 100))
        #imgAlpha = imgTest
        #imgAlpha.putalpha(mask)
        #imgBorder = PIL.Image.new("RGBA", (26, 10), "black")
        #imgBorder.paste(imgTest, (1,1))

        # add the POI to the output image
        background[0].paste(imgTest, (poi[2] * scaleFactor + canvasSize // 2 - 12, poi[3] * scaleFactor + canvasSize // 2 - 4))

        # save the base POI slightly scaled up for index.md
        imgOut = imgTest.resize((48, 24))
        imgOut.save(os.path.join(papyriOutputPath, poi[0] + str(poi[6]) + ".png"), "png")


# create the dimension output folder if they don't exsist
for d in dimDict:
    mapOutputPath = os.path.join(papyriOutputPath, "map", "dim", dimDict[d])
    if not os.path.exists(mapOutputPath):
        logging.info("Creating folder for %s", dimDict[d])
        os.makedirs(mapOutputPath)


# iterate over each dimension
for d in dimDict:
    # set the output path for map
    mapOutputPath = os.path.join(papyriOutputPath, "map", "dim", dimDict[d])

    # set the output path for PNG
    outPngFile = os.path.join(mapOutputPath, 'out{}.png'.format(d))

    logging.info("Saving .png for %s", dimDict[d])

    # save the PNG
    background[d].save(outPngFile)

    # set the output path of DZI
    outputDir = os.path.join(mapOutputPath, '{}_files'.format(dimDict[d]))

    # create a vips image
    dz = pyvips.Image.new_from_file(outPngFile, access='sequential')

    # delete the DZI if it exsists
    if os.path.exists(outputDir):
        shutil.rmtree(outputDir)
        
    logging.info("Saving DZI for %s", dimDict[d])

    # save the DZI
    dz.dzsave(os.path.join(mapOutputPath, '{}'.format(dimDict[d])), suffix=".png")

    #bg[d].dzsave(os.path.join(webdata, "newmap", 'out{}'.format(d)), suffix=".png")
    #bg.write_to_file("test.png")
