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
import numpy


# get the current running folder to find the font and template folders
cwd = os.path.dirname(os.path.abspath(__file__))

# setup the parser for command line options
parser = argparse.ArgumentParser(description='convert minecraft maps to the web')
parser.add_argument('--poi', action='store_true', help="generate POI")
parser.add_argument('--mcdata', help="input path to minecraft server data", required=True)
parser.add_argument('--output', help="output path for web stuff", required=True)
parser.add_argument("--size", help="size in blocks of map to render, centered on 0,0, default is 2000", type=int, default=2000)
parser.add_argument("--overlay", help="add overlay showing map IDs",
action='store_true')
parser.add_argument("--nostitch", help=
"disable generating the map, useful if you only want the overlay displayed", action="store_false")
parser.add_argument("--mapstats", help="generate stats on map coverage of selected size", action="store_true")


# Setup the logger
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

# get the args
args = parser.parse_args()
logging.info(args)

# are we redering the overlay?
overlay = args.overlay

# are we showing the map?
nostitch = args.nostitch

# Are we writing pois?
poi = args.poi

# are we creating stats?
mapstats = args.mapstats

# Set the input minecraft world folder
mcdata = args.mcdata

# Set the output web stuff folder
papyriOutputPath = args.output

# This is the font
fontPath = os.path.join(cwd, "04B_03B_.TTF")
font = PIL.ImageFont.truetype(fontPath,8)

# scale factor
scaleFactor = 1

# viewer zoom level
viewerZoom = args.size * 0.0092

# this is how much of the map is rendered
canvasSize = args.size * scaleFactor

# Format for the structure of a link pointing to a specific location on the map 
linkFormat = "map/#dim/overworld/{}/{}/" + str(viewerZoom)

# regular expression searching for coordinates
poiRE = "(.*)\n([one]?) ?(-?\d+), ?(-?\d+)\n(.*)"

# regular expression searching for HTML 8bit color codes
colorRE = "(#[0-9a-fA-F]{6})"

# dim dic for POI
dimDictShort = {"o": 0, "n": -1, "e": 1}

# dimension value to name dict
dimDict = {-1: "nether", 0: "overworld", 1: "end"}

# Header for the tag tables in markdown
tableHeader ="""

| |
|:-|
"""

# row format for each POI in markdown
poiFormat = "|![]({0}{6}.png) **{1}**<br>[{2}, {3}, {6}]({4})<br>{5}|\n"

poiMd = ""

if poi:
    # location of the player data files
    playerDatFilesPath = os.path.join(mcdata, "playerdata", "*.dat")

    # list of all the player data files
    playerDatFiles = glob.glob(playerDatFilesPath)

    logging.info("Found %s player(s)", len(playerDatFiles))

# empty defaultdict for all the tags
taggedPois = collections.defaultdict(list)

# empty list of all maps coords for links to maps
mapCoords = collections.defaultdict(list)

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

# if we're outputting POI
if poi:

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
                        title, dim, x, z, desc = each

                        # set dim tim overworld if no dim was specified
                        dim = 0 if not dim else dimDictShort[dim]

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
                        POI = (uuid, title, x,z, linkFormat.format(viewerx,viewerz), desc, num, color, dim)

                        logging.info(POI)

                        # if there's tags, append to the tag dict, otherwise, add to dict as untagged
                        if tags:

                            for tag in tags:
                                taggedPois[tag].append(POI)
                        else:
                            taggedPois["none"].append(POI)


    logging.info("Created %s tags", len(taggedPois))

# create the output folders if they don't exsist
if not os.path.exists(papyriOutputPath):
    logging.info("Creating output folders")
    os.makedirs(papyriOutputPath)
    os.makedirs(os.path.join(papyriOutputPath, "map"))

    # copy the web template files to the output folders

templatePath = os.path.join(cwd, "template")

requiredFiles = [("index.html", ""),
("index.md", ""),
("map/index.html", "map"),
("map/script.js", "map"),
("map/style.css", "map")]
for rFile in requiredFiles:
    if not os.path.exists(os.path.join(papyriOutputPath, rFile[0])):

        print("yup")
        logging.info("Copying {} template web files".format(rFile))
        shutil.copy(os.path.join(templatePath, rFile[0]),
                    os.path.join(papyriOutputPath, rFile[1]))

# path to maps
mapsInputGlob = os.path.join(mcdata, "data", "map*.dat")

# get all the maps
mapFiles = glob.glob(mapsInputGlob)

# sort the maps by modified time
mapFiles.sort(key=os.path.getmtime)

logging.info("Found %s maps", len(mapFiles))

# create a list for the map objects
mapFileObjs = []

logging.info("Parsing map .dat files")

# get all the map objects
for mapFile in mapFiles:
    mapFileObjs.append((os.path.basename(mapFile).split('.')[0],
    minecraftmap.Map(mapFile,eco=False)))


# sort them by zoom level
mapFileObjs.sort(key=lambda m: m[1].zoomlevel, reverse=True)

mapFileObjsByDim = collections.defaultdict(list)

for mapFileObj in mapFileObjs:
    mapFileObjsByDim[mapFileObj[1].dimension].append(mapFileObj)


# create the dimension output folder if they don't exsist
for d in dimDict:
    mapOutputPath = os.path.join(papyriOutputPath, "map", "dim", dimDict[d])
    if not os.path.exists(mapOutputPath):
        logging.info("Creating folder for %s", dimDict[d])
        os.makedirs(mapOutputPath)


# iterate over all the map objects
for d in dimDict:
    # put aside some stuff for stuff
    memory = []

    # create the large backgound iamge
    background = PIL.Image.new('RGBA', (canvasSize, canvasSize), (0, 0, 0, 0))

    # iterate over the maps
    for mt in mapFileObjsByDim[d]:
        m = mt[1]
        name = mt[0]
        dimension = d
        zoom = m.zoomlevel

        xc = int(m.centerxz[0]) * scaleFactor + canvasSize // 2
        zc = int(m.centerxz[1]) * scaleFactor + canvasSize // 2
        x = xc - 128 * 2 ** m.zoomlevel // 2 * scaleFactor
        z = zc - 128 * 2 ** m.zoomlevel // 2 * scaleFactor


        mapCoords[(xc, zc, zoom, d)].append(name)


        # skip if the center of the map isn't in the canvas
        if (x >= canvasSize * scaleFactor or x < 0) or (z >= canvasSize * scaleFactor or z < 0):
            continue

        if nostitch:
            logging.info("Stitching map at %s, %s zoom level %s in %s", m.centerxz[0], m.centerxz[1], zoom, dimDict[dimension])

            # create an image from the .dat data
            m.genimage()

            # rescale the image base on the zoom level
            m.rescale(num=scaleFactor)

            background.paste(m.im, (x, z), m.im)


    if poi:
        logging.info("Adding POIs to stiched map")

        # iterate over the tags to add POI to map
        for tag in sorted(taggedPois):
            # iterate over POI in tag
            for poi in [p for p in taggedPois[tag] if p[8] == d]:
                logging.info(poi)
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
                draw.text((14, 2), str(poi[6]), font=font)

                # add the player head
                imgTest.paste(PIL.Image.open(io.BytesIO(response.content)), (2, 2))

                #mask = imgTest.convert("L").point(lambda x: min(x, 100))
                #imgAlpha = imgTest
                #imgAlpha.putalpha(mask)
                #imgBorder = PIL.Image.new("RGBA", (26, 10), "black")
                #imgBorder.paste(imgTest, (1,1))

                # add the POI to the output image
                background.paste(imgTest, (poi[2] * scaleFactor + canvasSize //
                2 - 12, poi[3] * scaleFactor + canvasSize // 2 - 4))

                # save the base POI slightly scaled up for index.md
                imgOut = imgTest.resize((48, 24))
                imgOut.save(os.path.join(papyriOutputPath, poi[0] + str(poi[6]) + ".png"), "png")

    if overlay:
        colorList = ["red", "green", "blue", "yellow", "purple"]
        draw = PIL.ImageDraw.Draw(background)
        for m in [m for m in mapCoords.items() if m[0][3] == d]:
            logging.info("Overlaying {}".format(m))
            xc = m[0][0]
            zc = m[0][1]
            zoom = m[0][2]
            d = m[0][3]
            x = xc - 128 * 2 ** zoom // 2 * scaleFactor
            z = zc - 128 * 2 ** zoom // 2 * scaleFactor
            nameList = m[1]
            size = 128 * 2 ** zoom * scaleFactor
            mapNames = "\n".join(nameList)

            w, h = draw.textsize(mapNames, font=font)

            draw.rectangle([(x, z), (x + size, z + size)],
            outline=colorList[zoom])
            textx = xc-(w/2)
            textz = zc-(h/2)


            draw.text((textx - 1, textz), mapNames, font=font, fill="black")
            draw.text((textx + 1, textz), mapNames, font=font, fill="black")
            draw.text((textx, textz - 1), mapNames, font=font, fill="black")
            draw.text((textx, textz + 1), mapNames, font=font, fill="black")
            draw.text((textx, textz), mapNames, font=font, fill=colorList[zoom])

    numpy_image = numpy.asarray(background)
    height, width, bands = numpy_image.shape
    linear = numpy_image.reshape(width * height * bands)
    data = linear.data
    memory.append(data)
    vips_image = pyvips.Image.new_from_memory(data, width, height, bands, 'uchar')

    # set the output path for map
    mapOutputPath = os.path.join(papyriOutputPath, "map", "dim", dimDict[d])

    # set the output path for PNG
    #outPngFile = os.path.join(mapOutputPath, 'out{}.png'.format(d))

    #logging.info("Saving .png for %s", dimDict[d])

    # save the PNG
    # background[d].save(outPngFile)

    # set the output path of DZI
    outputDir = os.path.join(mapOutputPath, '{}_files'.format(dimDict[d]))

    # delete the DZI if it exsists
    if os.path.exists(outputDir):
        shutil.rmtree(outputDir)

    logging.info("Saving DZI for %s", dimDict[d])

    vips_image.dzsave(os.path.join(mapOutputPath, "{}".format(dimDict[d])), suffix=".png")

if mapstats:
    mapStats = {}

    '''
    # Creating map statistics
    for d in dimDict:
        mapStats.update([(d, len([a for a in background[d].getdata() if a[3] != 0]) / len(background[d].getdata()) * 100 )])


    mapStatsStr = ", ".join([dimDict[d] + " " + str(s) + "%" for d, s in mapStats.items()]) + "\n\n"
    '''

logging.info("Writing papyri.md")

if poi:
    # write the papyri.md file containing all the POI
    with open(os.path.join(papyriOutputPath, "papyri.md"), "w", encoding="utf-8") as poisFile:

            #poisFile.write("### Map stats\n")
            #poisFile.write(mapStatsStr)
            logging.info("Writing POI to papyri.md")
            # iterate over each tag
            for tag in sorted(taggedPois):
                #write the header for the tag
                poisFile.write("## [{}]".format(tag))
                poisFile.write(tableHeader)

                # iterate over all the POI in the tag
                for poi in taggedPois[tag]:
                    poisFile.write(poiFormat.format(*poi))









