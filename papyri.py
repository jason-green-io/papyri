#!/usr/bin/env python3
"""This is Papyri, a Minecraft in-game map renderer"""

__version__ = "0.8.4"
__author__ = "jason@green.io"

from pointsandrectangles import Point, Rect
import sys
import minecraftmap
import os
import glob
import PIL
import PIL.ImageOps
import PIL.ImageChops
import pyvips
import shutil
import io
import requests
from nbt.nbt import NBTFile, TAG_Long, TAG_Int, TAG_String, TAG_List, TAG_Compound
import re
import collections
import argparse
import logging
import json
import hashlib
import gzip
import jinja2

#mcfont = PIL.ImageFont.truetype(minecraftmap.fontpath,8)

# get the current running folder to find the font and template folders
cwd = os.path.dirname(os.path.abspath(__file__))

# setup the parser for command line options
parser = argparse.ArgumentParser(description='convert minecraft maps to the web')
parser.add_argument('--rendergrid', action='store_true', help="overlay chunk grid and mca file grid")
parser.add_argument('--overlaybanners', action='store_true', help="generate POI file and show banners")
parser.add_argument('--world', help="world folder or save folder (this is the folder level.dat is in)", required=True)
parser.add_argument('--includeunlimitedtracking', help="include maps that have unlimited tracking on, this includes older maps from previous Minecraft versions and treasure maps in +1.13", action="store_true")
parser.add_argument('--output', help="output path for web stuff", required=True)
parser.add_argument('--zoomlevel', help="size of maps generated in mc zoom levels, 8 = 65k, 7 = 32k", choices=["4", "5", "6", "7", "8"], default=5)
parser.add_argument("--rendermapids", help="overlay map IDs", action='store_true')
parser.add_argument("--renderspawnchunks", action='store_true', help="overlay the spawn chunks")
parser.add_argument("--blendmaps", action="store_true", help="blend maps with the same center and zoom level")
parser.add_argument("--sortmaps", default="time", choices=["time", "id"], help="sort maps by last modified or by id (if they were copied and the file metadata is gone)")
parser.add_argument("--overlayplayers", action='store_true', help="show last known player locations")


# Setup the logger
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

# get the args
args = parser.parse_args()

if args.renderspawnchunks and not args.rendergrid:
    parser.error("grid must be on to show spawn chunks")
logging.info(args)


# This is the font
fontPath = os.path.join(cwd, "template/mcfont/font/minecraft_font.ttf")
font = PIL.ImageFont.truetype(fontPath, 8)

# scale factor
scaleFactor = 1

# this is how much of the map is rendered
canvasSize = 2 ** (8 + int(args.zoomlevel))

viewerZoom = 1

# Format for the structure of a link pointing to a specific location on the map
linkFormat = "map/{}/"

# regular expression searching for coordinates
poiRE = "(.*)\n([one]?) ?(-?\d+), ?(-?\d+)\n(.*)"

# regular expression searching for HTML 8bit color codes
colorRE = "(#[0-9a-fA-F]{6})"

# dim dic for POI
dimDictShort = {"o": 0, "n": -1, "e": 1}

# dimension value to name dict
dimDict = {-1: "nether", 0: "overworld", 1: "end"}
dimColour = {-1: "#3E1A19", 0: "#575757", 1: "#C2C688"}

mapLinkFormat = "map/{dim}/#zoom=0.02&x={x}&y={z}"



# empty defaultdict for all the tags
bannerJson = []

# empty list of all maps coords for links to maps

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

'''
# if we're outputting POI
if poiArg:

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

            if "papyri" in bookName.lower():

                # iterate over the pages
                for page in book.get("tag",{}).get("pages", []):
                    #iterate over every POI found on a page
                    for each in  re.findall(poiRE, page):

                        # get the stuff from the POI
                        title, dim, x, z, desc = each

                        # set dim to overworld if no dim was specified
                        d = 0 if not dim else dimDictShort[dim]

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
                            color = colors[0]
                        else:
                            color = "#ffffff"

                        uuidnum = uuid + str(num)

                        # prepare a POI for writing
                        POI = {"num": num, "color": color, "uuid": uuid, "type": "book", "image": uuidnum + ".png", "title": title, "x": x, "z": z, "desc": desc, "d": d, "maplink": mapLinkFormat.format(x=x, z=z, dim=dimDict[d]), "dim": dimDict[d]}

                        logging.info(POI)

                        # if there's tags, append to the tag dict, otherwise, add to dict as untagged
                        if tags:

                            for tag in tags:
                                taggedPois[tag].append(POI)
                        else:
                            taggedPois["none"].append(POI)

'''

templatePath = os.path.join(cwd, "template")

if not os.path.exists(args.output):

    logging.info("Copying template web files")
    shutil.copytree(templatePath, args.output)

# path to maps
mapsInputGlob = os.path.join(args.world, "data", "map*.dat")

# path to playerfile
playerdataInputGlob = os.path.join(args.world, "playerdata", "*.dat")

# level.dat
if args.renderspawnchunks:
    os.path.join(args.world, "level.dat")
    try:
        with gzip.open(os.path.join(args.world, "level.dat"), "rb") as buffer:
            nbtData = NBTFile(buffer=buffer)

        levelDatObj = unpack_nbt(nbtData)
        logging.info("Loaded level.dat")
        print(levelDatObj)
    except:
        logging.info("Couldn't load level.dat")
        sys.exit(1)

def getSpawnChunkPoints():
    # figure out the spawnchunk chunks
    spawnX = levelDatObj["Data"]["SpawnX"]
    spawnZ = levelDatObj["Data"]["SpawnZ"]

    minSpawnX = spawnX - 128
    maxSpawnX = spawnX + 128

    minChunkX = minSpawnX >> 4
    maxChunkX = maxSpawnX >> 4

    ChunkX = [c for c in range(minChunkX, maxChunkX + 1) if c * 16 - 8 >= minSpawnX and c * 16 - 8 <= maxSpawnX]


    minSpawnZ = spawnZ - 128
    maxSpawnZ = spawnZ + 128

    minChunkZ = minSpawnZ >> 4
    maxChunkZ = maxSpawnZ >> 4

    ChunkZ = [c for c in range(minChunkZ, maxChunkZ + 1) if c * 16 - 8 >= minSpawnZ and c * 16 - 8 <= maxSpawnZ]

    spawnChunks = [(x * 16, z * 16) for x in ChunkX for z in ChunkZ]
    return spawnChunks


playerFiles = glob.glob(playerdataInputGlob)

playerObjs = collections.defaultdict(list)

for playerFile in playerFiles:
    nbtObject = NBTFile(playerFile)
    nbtDict = unpack_nbt(nbtObject)
    newDict = {"uuid": os.path.basename(playerFile).split(".")[0], "data": nbtDict}
    print(newDict["data"]["Dimension"])
    playerObjs[nbtDict["Dimension"]].append(newDict)

print(playerObjs)

# get all the maps
mapFiles = glob.glob(mapsInputGlob)


def sortByInt(name):
    return int(os.path.basename(name).strip("map_").strip(".dat"))

# sort the maps by modified time
if args.sortmaps == "id":
    mapFiles.sort(key=sortByInt)
elif args.sortmaps == "time":
    mapFiles.sort(key=os.path.getmtime)

logging.info("Found %s maps", len(mapFiles))

# create a list for the map objects
mapFileObjs = []

logging.info("Parsing map .dat files")


bigMaps = set()
banners = collections.defaultdict(list)

# get all the map objects
for mapFile in mapFiles:
    mapObj = minecraftmap.Map(mapFile,eco=True)
    if args.includeunlimitedtracking:
        mapFileObjs.append({"name": os.path.basename(mapFile).split('.')[0], "time": os.path.getmtime(mapFile), "object":mapObj})
    else:
        if not mapObj.unlimitedTracking:
            mapFileObjs.append({"name": os.path.basename(mapFile).split('.')[0], "time": os.path.getmtime(mapFile), "object":mapObj})
    banners[mapObj.dimension].extend(mapObj.banners)


logging.debug(banners)

# sort them by zoom level
#mapFileObjs.sort(key=lambda m: m[1].zoomlevel, reverse=True)

mapFileObjsByDim = collections.defaultdict(lambda:
    collections.defaultdict(collections.OrderedDict))

mapLabelsByDim = collections.defaultdict(lambda:
    collections.defaultdict(lambda: collections.defaultdict(set)))

for mapFileObj in mapFileObjs:
    mapObj = mapFileObj["object"]
    time = mapFileObj["time"]
    name = mapFileObj["name"]
    zoom = int(mapObj.zoomlevel)
    d = mapObj.dimension
    xc = mapObj.centerxz[0]
    zc = mapObj.centerxz[1]

    p1 = Point(xc - 128 * 2 ** zoom // 2,
                zc- 128 * 2 ** zoom // 2)
    p2 = Point(xc + 128 * 2 ** zoom // 2,
                zc + 128 * 2 ** zoom // 2)
    rect = Rect(p1, p2)

    p3 = Point(p1.as_tuple()[0], p2.as_tuple()[1])
    p4 = Point(p2.as_tuple()[0], p1.as_tuple()[1])

    for p in [p1, p2, p3, p4]:
        x = p.as_tuple()[0]
        z = p.as_tuple()[1]

        bp1 = Point(divmod(x - 64, canvasSize)[0] * canvasSize - 64, divmod(z -
        64, canvasSize)[0] * canvasSize - 64)
        bp2 = bp1 + Point(canvasSize, canvasSize)

        bigMap = Rect(bp1, bp2)

        btl = bigMap.top_left().as_tuple()
        bbr = bigMap.bottom_right().as_tuple()

        if bigMap.overlaps(rect):
            mapFileObjsByDim[d][(btl,bbr)][name] = mapObj
            mapLabelsByDim[d][(btl,bbr)][(xc, zc, zoom)].add(name)
logging.debug(mapLabelsByDim)

# create the dimension output folder if they don't exsist
for d in dimDict:
    mapOutputPath = os.path.join(args.output, "map", dimDict[d])
    if not os.path.exists(mapOutputPath):
        logging.info("Creating folder for %s", dimDict[d])
        os.makedirs(mapOutputPath)


# iterate over all the map objects
for d in dimDict:
    bigMaps = mapFileObjsByDim[d].items()
    logging.info("Rendering {} big maps for {}".format(len(bigMaps), dimDict[d]))
    # put aside some stuff for stuff
    for bigMap in bigMaps:

        bigMapName = "{}_{}_{}".format(d, *bigMap[0][0])

        # create the large backgound iamge
        #background = PIL.Image.new('RGB', (canvasSize - (canvasSize // 64) * 2, canvasSize - (canvasSize // 64) * 2), (204, 178, 132))
        #background = PIL.ImageOps.expand(background ,border=canvasSize // 64, fill=(124, 109, 82))

        background = PIL.Image.open(os.path.join(cwd, "template", "itemframe.png"))
        background = background.resize((canvasSize, canvasSize))
        background.putalpha(255)

        p1 = Point(*bigMap[0][0])
        p2 = Point(*bigMap[0][1])
        mapsImageList = [PIL.Image.new("RGBA", background.size, (255,255,255,0)) for x in range(0, 5)]

        # iterate over the maps
        for littleMap in bigMap[1].items():
            m = littleMap[1]
            name = littleMap[0]
            dimension = d
            zoom = m.zoomlevel

            xc = int(m.centerxz[0])
            zc = int(m.centerxz[1])
            centerPoint = Point(xc, zc) - p1

            x = xc - 128 * 2 ** m.zoomlevel // 2 * scaleFactor
            z = zc - 128 * 2 ** m.zoomlevel // 2 * scaleFactor

            topLeft = Point(x,z) - p1
            bottomRight = Point(x + 128 * 2 ** m.zoomlevel, z + 128 * 2 ** m.zoomlevel) - p1

            # skip if the center of the map isn't in the canvas

            logging.info("Stitching map at %s, %s zoom level %s relative coords %s, %s in %s",
            x, z, zoom, topLeft, bottomRight, bigMapName)

            # create an image from the .dat data
            m.genimage()

            # rescale the image base on the zoom level
            mapOriginal = m.im
            #pixels = mapOriginal.load()
            #for i in range(mapOriginal.size[0]):
            #    for j in range(mapOriginal.size[1]):
            #            if pixels[i,j][3] != 0:
            #                pixels[i,j] = (pixels[i,j][0], pixels[i,j][1], pixels[i,j][2], 64)


            mapScaled = mapOriginal.resize((128 * 2 ** m.zoomlevel, 128 * 2 ** m.zoomlevel))
            newLayer = PIL.Image.new("RGBA", background.size)
            newLayer.paste(mapScaled, topLeft.as_tuple() + bottomRight.as_tuple(), mapScaled)

            pixels1 = mapsImageList[zoom].load()
            pixels2 = newLayer.load()
            for x in range(topLeft.x, topLeft.x + mapScaled.size[0]):
                for z in range(topLeft.y, topLeft.y + mapScaled.size[1]):
                    if pixels1[x,z][3] == 0:
                        pixels1[x,z] = (pixels2[x,z][0], pixels2[x,z][1], pixels2[x,z][2], pixels2[x,z][3])
                    else:
                        if args.blendmaps:
                            pixels1[x,z] = ((pixels2[x,z][0] + pixels1[x,z][0]) // 2, (pixels2[x,z][1] + pixels1[x,z][1]) // 2, (pixels2[x,z][2] + pixels1[x,z][2]) // 2, pixels2[x,z][3])
                        else:
                            pixels1[x,z] = (pixels2[x,z][0], pixels2[x,z][1], pixels2[x,z][2], pixels2[x,z][3])

            #mapsImageList[zoom] = PIL.ImageChops.add(mapsImageList[zoom], newLayer, scale=2)
            #mapsImageList[zoom].paste(mapScaled, topLeft.as_tuple() + bottomRight.as_tuple(), mapScaled)
        for mapsImage in mapsImageList[::-1]:
            #pixels = mapsImage.load()
            #for i in range(mapsImage.size[0]):
            #    for j in range(mapsImage.size[1]):
            #            if pixels[i,j][3] != 0:
            #                pixels[i,j] = (pixels[i,j][0], pixels[i,j][1], pixels[i,j][2], 255)

            background.paste(mapsImage, mask=mapsImage)

        if args.rendermapids:

            #colorList = ["red", "green", "blue", "yellow", "purple"]
            alpha = 128
            colorList = [(255,0,0,alpha), (0,255,0,alpha), (0,0,255,alpha), (128,128,0,alpha), (255,0,255,alpha)]
            overlays = PIL.Image.new("RGBA", background.size, (255,255,255,0))


            logging.debug(mapLabelsByDim[d][bigMap[0]])
            for uniqMap in mapLabelsByDim[d][bigMap[0]].items():
                box = PIL.Image.new("RGBA", (128, 128), (255,255,255,0))
                draw = PIL.ImageDraw.Draw(box)
                ((xc, zc, zoom), names) = uniqMap

                logging.info("Overlaying {}".format(uniqMap))

                centerPoint = Point(xc, zc) - p1

                x = xc - 128 * 2 ** zoom // 2 * scaleFactor
                z = zc - 128 * 2 ** zoom // 2 * scaleFactor

                topLeft = Point(x,z) - p1
                #bottomRight = topLeft + Point(128 * 2 ** zoom, 128 * 2 ** zoom) - Point(1, 1)

                mapNames = "\n".join(names)

                w, h = draw.textsize(mapNames, font=font)

                draw.rectangle([(0,0), (127, 127)], outline=colorList[zoom])
                textx = 64 - (w / 2)
                textz = 64 - (h / 2)

                shadow = (0,0,0,64)
                draw.text((textx - 1, textz), mapNames, font=font, fill=shadow)
                draw.text((textx + 1, textz), mapNames, font=font, fill=shadow)
                draw.text((textx, textz - 1), mapNames, font=font, fill=shadow)
                draw.text((textx, textz + 1), mapNames, font=font, fill=shadow)
                draw.text((textx, textz), mapNames, font=font, fill=colorList[zoom])

                box = box.resize((128 * 2 ** zoom, 128 * 2 ** zoom))

                overlays.alpha_composite(box, dest=topLeft.as_tuple())
            background.alpha_composite(overlays)

        if args.rendergrid:
            if args.renderspawnchunks:
                spawnChunkPoints = getSpawnChunkPoints()

            chunkGridImage = PIL.Image.new("RGBA", background.size, (255,255,255,0))
            draw = PIL.ImageDraw.Draw(chunkGridImage)

            for chunkX in range((p1.x >> 4) * 16, (p2.x >> 4) * 16 + 16, 16):
                for chunkZ in range((p1.y >> 4) * 16, (p2.y >> 4) * 16 + 16, 16):
                    chunkPointAbs = Point(chunkX, chunkZ)
                    chunkPoint1 = chunkPointAbs - p1
                    chunkPoint2 = chunkPoint1 + Point(15, 15)
                    if args.renderspawnchunks:
                        if chunkPointAbs.as_tuple() in spawnChunkPoints:
                            draw.rectangle([chunkPoint1.as_tuple(), chunkPoint2.as_tuple()], fill=(0,255,255,64))
                    draw.rectangle([chunkPoint1.as_tuple(), chunkPoint2.as_tuple()], outline=(172,172,172,64))


            regionGridImage = PIL.Image.new("RGBA", background.size, (255,255,255,0))
            draw = PIL.ImageDraw.Draw(regionGridImage)

            for regionX in range((p1.x >> 9) * 512, (p2.x >> 9) * 512 + 512, 512):
                for regionZ in range((p1.y >> 9) * 512, (p2.y >> 9) * 512 + 512, 512):
                    regionPoint1 = Point(regionX, regionZ) - p1
                    regionPoint2 = regionPoint1 + Point(511, 511)
                    draw.rectangle([regionPoint1.as_tuple(), regionPoint2.as_tuple()], outline=(255,255,255,64))

            grid = PIL.Image.alpha_composite(chunkGridImage, regionGridImage)
            background.alpha_composite(grid)
        """
        numpy_image = numpy.asarray(background)
        height, width, bands = numpy_image.shape
        linear = numpy_image.reshape(width * height * bands)
        data = linear.data
        memory.append(data)

        vips_image = pyvips.Image.new_from_memory(data, width, height, bands, 'uchar')
        del memory
        """
        # set the output path for map
        mapOutputPath = os.path.join(args.output, "map", dimDict[d])

        # set the output path for PNG
        outPngFile = os.path.join(mapOutputPath, '{}.png'.format(bigMapName))

        #logging.info("Saving .png for %s", dimDict[d])


        # set the output path of DZI
        outputDir = os.path.join(mapOutputPath, 'temp_files')

        # delete the DZI if it exsists
        if os.path.exists(outputDir):
            shutil.rmtree(outputDir)

        logging.info("Saving PNG for %s", bigMapName)
        # save the PNG
        with open(outPngFile, "wb+") as f:
            background.save(f, format="png")

        logging.info("Converting png to deepzoom")
        pyvips.Image.new_from_file(outPngFile, access='sequential').dzsave(os.path.join(mapOutputPath, "temp"), suffix=".png")
        if os.path.exists(os.path.join(mapOutputPath, bigMapName + ".dzi")):
            os.remove(os.path.join(mapOutputPath, bigMapName + ".dzi"))

        shutil.move(os.path.join(mapOutputPath, "temp.dzi"), os.path.join(mapOutputPath, bigMapName + ".dzi"))
        if os.path.exists(os.path.join(mapOutputPath, bigMapName + "_files")):
            shutil.rmtree(os.path.join(mapOutputPath, bigMapName + "_files"))

        shutil.move(os.path.join(mapOutputPath, "temp_files"), os.path.join(mapOutputPath, bigMapName + "_files"))




for d in dimDict:
    poiOverlay = collections.namedtuple("poiOverlay", ["id", "x", "y", "checkResize", "placement"])
    poiOverlays = set()
    poiImages = []
    '''
    if poiArg:
        logging.info("Adding POIs to stiched map")


        # iterate over the tags to add POI to map
        for tag in sorted(taggedPois):
            # iterate over POI in tag
            for poi in [p for p in taggedPois[tag] if p["d"] == d and p["type"] == "book"]:

                logging.info(poi)
                # get POI player head
                response = requests.get("https://mc-heads.net/avatar/{}/16".format(poi["uuid"]))
                avatar = PIL.Image.open(io.BytesIO(response.content))

                rgbBack = tuple(int(poi["color"].lstrip('#')[i:i+2], 16) for i in (0, 2 ,4))

                textColor = "#000000" if (rgbBack[0] * 0.299 + rgbBack[1] * 0.587 + rgbBack[2] * 0.114) > 186 else "#ffffff"


                poiBack = PIL.Image.open(os.path.join(cwd, "template", "bigbook.png"))
                # object to draw on base POI
                textBack = PIL.Image.new("RGBA", (8, 8), poi["color"])

                draw = PIL.ImageDraw.Draw(textBack)
                w, h = draw.textsize(str(poi["num"]), font=font)
                draw.text((8 // 2 - w // 2 , 1), str(poi["num"]), font=font, fill=textColor)
                textBack = textBack.resize((16, 16))
                """
                # get the number of colors in POI
                totalColors = len(color)

                # calculate how high a color bar will be
                rectHeight = 16 // totalColors

                # iterate over each color
                for each in enumerate(color):
                    # draw a color bar on base POI
                    point1 = (0, rectHeight * each[0])
                    point2 = (7, rectHeight * each[0] + rectHeight)
                    draw.rectangle([point1, point2], fill=each[1])
                """



                poiBack.paste(avatar, (7, 3))
                poiBack.paste(textBack, (7, 19))

                # add the POI id as a number

                # add the player head


                #mask = imgTest.convert("L").point(lambda x: min(x, 100))
                #imgAlpha = imgTest
                #imgAlpha.putalpha(mask)
                #imgBorder = PIL.Image.new("RGBA", (26, 10), "black")
                #imgBorder.paste(imgTest, (1,1))

                # add the POI to the output image


                uuidnum = poi["uuid"] + str(poi["num"])

                # save the base POI slightly scaled up for index.md

                poiBack.save(os.path.join(papyriOutputPath, poi["image"]), "png")

                jsonForIndex = {"id": uuidnum, "x": poi["x"], "y": poi["z"], "placement": "TOP_LEFT", "checkResize": False}
                if jsonForIndex not in poiOverlays:
                    poiOverlays.append(jsonForIndex)

                imgForIndex = '<img class="poiOverlay" id="{uuidnum}" src="../../{uuidnum}.png" title="{title}" alt="{title}">'.format(uuidnum=uuidnum, title=poi["title"])
                if imgForIndex not in poiImages:
                    poiImages.append(imgForIndex)
    '''
    if args.overlaybanners:
        for playerObj in playerObjs[d]:
            data = playerObj["data"]
            uuid = playerObj["uuid"]
            x = data["Pos"][0]
            z = data["Pos"][2]

            overlayId = hashlib.md5(uuid.encode("utf-8")).hexdigest()

            poiOverlays.add(poiOverlay(overlayId, x, z, False, "CENTER"))

            poiImages.append(dict(h=32, w=32, id=overlayId, src="https://minotar.net/avatar/{uuid}/32".format(uuid=uuid), title=uuid, alt=uuid))
    if args.overlaybanners:
        for banner in banners[d]:
            color = banner["Color"]
            x = banner["Pos"]["X"]
            z = banner["Pos"]["Z"]
            y = banner["Pos"]["Y"]
            coords = "{} {} {}".format(str(x), str(y), str(z))
            name = json.loads(banner.get("Name", '{}')).get("text", "")

            #tags = re.findall("\[(.*?)\]", name)

            name = re.subn("\[(.*?)\]", r"[\1](#\1)", name)[0]

            POI = {"title": name, "x": x, "z": z, "color": color, "d": d, "dim": dimDict[d], "maplink": mapLinkFormat.format(x=x, z=z, dim=dimDict[d])}

            logging.info(POI)

            # if there's tags, append to the tag dict, otherwise, add to dict as untagged
            '''
            if tags:

                for tag in tags:
                    taggedPois[tag].append(POI)
            else:
                taggedPois["none"].append(POI)
            '''
            bannerJson.append(POI)

            overlayIdText = name + color + str(x) + str(z)
            overlayId = hashlib.md5(overlayIdText.encode("utf-8")).hexdigest()

            poiOverlays.add(poiOverlay(overlayId, x, z, False, "CENTER"))


            bannerImage = PIL.Image.open(os.path.join(templatePath, "{color}banner.png".format(color=color)))

            poiImage = PIL.Image.new("RGBA", (256, 64), (255, 255, 255, 0))
            if name:
                draw = PIL.ImageDraw.Draw(poiImage)
                w, h = draw.textsize(name, font=font)
                #poiImage = poiImage.resize((w, 64))
                draw = PIL.ImageDraw.Draw(poiImage)
                textX = 127 - (w // 2)
                textY = 34
                draw.rectangle((textX, textY, textX + w, textY + h), fill=(0, 0, 0, 160))
                draw.text((textX, textY), name, font=font, fill=(255, 255, 255, 255))

                poiImage.paste(bannerImage, (127 - 12, 0))
            else:
                #poiImage = poiImage.resize((24, 64))
                poiImage.paste(bannerImage, (127 - 12, 0))


            imageNameText = color + name
            imageName = hashlib.md5(imageNameText.encode("utf-8")).hexdigest()

            poiImage.save(os.path.join(args.output, imageName + ".png"))

            poiImages.append(dict(h=64, w=256, id=overlayId, src="../../{imageName}".format(imageName), title=coords, alt=coords))

    mapOutputPath = os.path.join(args.output, "map", dimDict[d])
    logging.info("Generating index.html file for {}".format(dimDict[d]))
    # put aside some stuff for stuff
    tileSources = []
    for bigMap in mapFileObjsByDim[d].items():
        bigMapName = "{}_{}_{}".format(d, *bigMap[0][0])
        x, y = bigMap[0][0]


        tileSources.append(dict(tileSource="{}.dzi".format(bigMapName), x=x,
        y=y, width=canvasSize))



    tileSources

    colour = dimColour[d]

    overlays = list(dict((v.id, v._asdict()) for v in poiOverlays).values())

    images = poiImages

    templateLoader = jinja2.FileSystemLoader(searchpath="./template")
    env = jinja2.Environment(
            loader=templateLoader,
            autoescape=jinja2.select_autoescape(['html', 'xml'])
    )

    template = env.get_template('template.html')

    output = template.render(iimages=images, tileSources=tileSources, colour=colour, overlays=overlays, images=images)

    with open(os.path.join(mapOutputPath, "index.html"), "+w", encoding="utf-8") as outFile:
        outFile.write(output)

# write the papyri.md file containing all the POI
with open(os.path.join(args.output, "papyri.json"), "w", encoding="utf-8") as poisFile:

    logging.info("Writing POI to papyri.json")
    json.dump(bannerJson, poisFile)






