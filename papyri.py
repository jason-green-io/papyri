#!/usr/bin/env python3

# This is Papyri, a Minecraft in-game map rendered
# version 0.6
# created by jason@green.io


from pointsandrectangles import Point, Rect
import sys
import minecraftmap
import os
import glob
import PIL
import PIL.ImageOps
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
import json
import hashlib

mcfont = PIL.ImageFont.truetype(minecraftmap.fontpath,8)

# get the current running folder to find the font and template folders
cwd = os.path.dirname(os.path.abspath(__file__))

# setup the parser for command line options
parser = argparse.ArgumentParser(description='convert minecraft maps to the web')
parser.add_argument('--poi', action='store_true', help="generate POI file, this outputs papyri.md that can be used with http://dynalon.github.io/mdwiki/#!index.md to show on the web")
parser.add_argument('--mcdata', help="input path to minecraft server data", required=True)
parser.add_argument('--output', help="output path for web stuff", required=True)
parser.add_argument('--zoomlevel', help="size of maps generated in mc zoom levels, 8 = 65k, 7 = 32k", choices=["5","6","7","8"], default=6)
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
# Header for the tag tables in markdown
tableHeader ="""

| | |
|:-|:-|
"""

# row format for each POI in markdown
poiFormat = "|![]({0}{6}.png)|**{1}**<br>[{2}, {3}, {6}]({4})<br>{5}|\n"

poiMd = ""

indexTemplateTop = """
<title>Papyri</title>
<style>
body {
  margin: 0;
}
</style>
<div id="openseadragon1" style="background-color: replaceThisWithTheBackgroundColour; margin: 0 auto; width: 100%; height: 100%;"></div>
<script src="../../openseadragon/openseadragon.min.js"></script>
<script   src="https://code.jquery.com/jquery-3.3.1.min.js"   integrity="sha256-FgpCb/KJQlLNfOu91ta32o/NMZxltwRo8QtmkMRdAu8="   crossorigin="anonymous"></script>
<script type="text/javascript">
    var viewer = OpenSeadragon({
        id: "openseadragon1",
        showNavigator: true,
        //minZoomImageRatio: 0.5,
        //defaultZoomLevel: 64,
        //maxZoomLevel: 6,
        //minZoomLevel: 64,
        maxZoomPixelRatio: 30,
        //minPixelRatio: 1.5,
        imediateRender: true,
        prefixUrl: "../../images/",
navImages: {
    zoomIn: {
    REST: 'zoominrest.png',
    GROUP: 'zoomin.png',
    HOVER: 'zoomindown.png',
    DOWN: 'zoomindown.png'
    },
    zoomOut: {
    REST: 'zoomoutrest.png',
    GROUP: 'zoomout.png',
    HOVER: 'zoomoutdown.png',
    DOWN: 'zoomoutdown.png'
        },
    home: {
    REST: 'homerest.png',
    GROUP: 'home.png',
    HOVER: 'homedown.png',
    DOWN: 'homedown.png'
        },
    fullpage: {
    REST: 'fullscreenrest.png',
    GROUP: 'fullscreen.png',
    HOVER: 'fullscreendown.png',
    DOWN: 'fullscreendown.png'
        }

    },


"""
indexTemplateBottom = """

});
viewer.addHandler('open', () => {
      let toggleOverlayButton = new OpenSeadragon.Button({
        tooltip: 'Toggle Overlays',
        srcRest: '../../images/poirest.png',
        srcGroup: '../../images/poi.png',
        srcHover: '../../images/poidown.png',
        srcDown: '../../images/poidown.png',

      });

    viewer.addControl(toggleOverlayButton.element, { anchor: OpenSeadragon.ControlAnchor.TOP_LEFT });
    toggleOverlayButton.addHandler("click", function (data) {
    p_lays=document.getElementsByClassName("poioverlay");
    for(let i=0;i<p_lays.length;i++)p_lays[i].style.display==="none"?p_lays[i].style.display="block":p_lays[i].style.display="none";


    });
    
    });
</script>
"""

if poi:
    # location of the player data files
    playerDatFilesPath = os.path.join(mcdata, "playerdata", "*.dat")

    # list of all the player data files
    playerDatFiles = glob.glob(playerDatFilesPath)

    logging.info("Found %s player(s)", len(playerDatFiles))

# empty defaultdict for all the tags
taggedPois = collections.defaultdict(list)

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

            if "papyri" in bookName.lower():

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
                            color = colors[0]
                        else:
                            color = "#ffffff"

                        # prepare a POI for writing
                        POI = (uuid, title, x,z, linkFormat.format(dimDict[dim]), desc, num, color, dim)

                        logging.info(POI)

                        # if there's tags, append to the tag dict, otherwise, add to dict as untagged
                        if tags:

                            for tag in tags:
                                taggedPois[tag].append(POI)
                        else:
                            taggedPois["none"].append(POI)


    logging.info("Created %s tags", len(taggedPois))
"""
# create the output folders if they don't exsist
if not os.path.exists(papyriOutputPath):
    logging.info("Creating output folders")
    os.makedirs(papyriOutputPath)
    os.makedirs(os.path.join(papyriOutputPath, "map"))

    # copy the web template files to the output folders
"""
templatePath = os.path.join(cwd, "template")

if not os.path.exists(papyriOutputPath):
    
    logging.info("Copying template web files")
    shutil.copytree(templatePath, papyriOutputPath)

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


bigMaps = set()
banners = collections.defaultdict(list)

# get all the map objects
for mapFile in mapFiles:
    mapObj = minecraftmap.Map(mapFile,eco=False)
    mapFileObjs.append((os.path.basename(mapFile).split('.')[0], mapObj))
    banners[mapObj.dimension].extend(mapObj.banners)

print(banners)
    
# sort them by zoom level
mapFileObjs.sort(key=lambda m: m[1].zoomlevel, reverse=True)

mapFileObjsByDim = collections.defaultdict(lambda:
    collections.defaultdict(collections.OrderedDict))

mapLabelsByDim = collections.defaultdict(lambda:
    collections.defaultdict(lambda: collections.defaultdict(set)))

for mapFileObj in mapFileObjs:
    mapObj = mapFileObj[1]
    name = mapFileObj[0]
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
print(mapLabelsByDim)

# create the dimension output folder if they don't exsist
for d in dimDict:
    mapOutputPath = os.path.join(papyriOutputPath, "map", dimDict[d])
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
        p1 = Point(*bigMap[0][0])
        p2 = Point(*bigMap[0][1])

        # contextRect = Rect(Point())
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


            # skip if the center of the map isn't in the canvas

            if nostitch:
                logging.info("Stitching map at %s, %s zoom level %s relative coords %s in %s",
                x, z, zoom, topLeft, bigMapName)

                # create an image from the .dat data
                m.genimage()

                # rescale the image base on the zoom level
                m.rescale(num=scaleFactor)

                background.paste(m.im, topLeft.as_tuple(), m.im)


        if overlay:

            colorList = ["red", "green", "blue", "yellow", "purple"]
            draw = PIL.ImageDraw.Draw(background)

            print(mapLabelsByDim[d][bigMap[0]])
            for uniqMap in mapLabelsByDim[d][bigMap[0]].items():

                ((xc, zc, zoom), names) = uniqMap

                logging.info("Overlaying {}".format(uniqMap))

                centerPoint = Point(xc, zc) - p1

                x = xc - 128 * 2 ** zoom // 2 * scaleFactor
                z = zc - 128 * 2 ** zoom // 2 * scaleFactor

                topLeft = Point(x,z) - p1
                bottomRight = topLeft + Point(128 * 2 ** zoom, 128 * 2 ** zoom)

                mapNames = "\n".join(names)

                w, h = draw.textsize(mapNames, font=font)

                draw.rectangle([topLeft.as_tuple(), bottomRight.as_tuple()], outline=colorList[zoom])
                textx = centerPoint.as_tuple()[0] - (w / 2)
                textz = centerPoint.as_tuple()[1] - (h / 2)


                draw.text((textx - 1, textz), mapNames, font=font, fill="black")
                draw.text((textx + 1, textz), mapNames, font=font, fill="black")
                draw.text((textx, textz - 1), mapNames, font=font, fill="black")
                draw.text((textx, textz + 1), mapNames, font=font, fill="black")
                draw.text((textx, textz), mapNames, font=font, fill=colorList[zoom])
        """
        numpy_image = numpy.asarray(background)
        height, width, bands = numpy_image.shape
        linear = numpy_image.reshape(width * height * bands)
        data = linear.data
        memory.append(data)
        
        vips_image = pyvips.Image.new_from_memory(data, width, height, bands, 'uchar')
        del memory
        """
        if nostitch:
            # set the output path for map
            mapOutputPath = os.path.join(papyriOutputPath, "map", dimDict[d])

            # set the output path for PNG
            outPngFile = os.path.join(mapOutputPath, '{}.png'.format(bigMapName))

            #logging.info("Saving .png for %s", dimDict[d])


            # set the output path of DZI
            outputDir = os.path.join(mapOutputPath, '{}_files'.format(bigMapName))

            # delete the DZI if it exsists
            if os.path.exists(outputDir):
                shutil.rmtree(outputDir)

            logging.info("Saving PNG for %s", bigMapName)
            # save the PNG
            with open(outPngFile, "wb+") as f:
                background.save(f, format="png")

            logging.info("Converting png to deepzoom")
            pyvips.Image.new_from_file(outPngFile, access='sequential').dzsave(os.path.join(mapOutputPath, bigMapName), suffix=".png")

if mapstats:
    mapStats = {}

    '''
    # Creating map statistics
    for d in dimDict:
        mapStats.update([(d, len([a for a in background[d].getdata() if a[3] != 0]) / len(background[d].getdata()) * 100 )])


    mapStatsStr = ", ".join([dimDict[d] + " " + str(s) + "%" for d, s in mapStats.items()]) + "\n\n"
    '''

logging.info("Writing papyri.md")



for d in dimDict:
    poiOverlays = []
    poiImages = []

    if poi:
        logging.info("Adding POIs to stiched map")

        
        # iterate over the tags to add POI to map
        for tag in sorted(taggedPois):
            # iterate over POI in tag
            for poi in [p for p in taggedPois[tag] if p[8] == d]:
                uuid, title, x, z, link, desc, num, color, dim = poi
                
                logging.info(poi)
                # get POI player head 
                response = requests.get("https://mc-heads.net/avatar/{}/16".format(uuid))
                avatar = PIL.Image.open(io.BytesIO(response.content))

                rgbBack = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2 ,4))

                textColor = "#000000" if (rgbBack[0] * 0.299 + rgbBack[1] * 0.587 + rgbBack[2] * 0.114) > 186 else "#ffffff"
                
                
                poiBack = PIL.Image.open(os.path.join(cwd, "template", "bigbook.png"))
                # object to draw on base POI
                textBack = PIL.Image.new("RGBA", (8, 8), color)

                draw = PIL.ImageDraw.Draw(textBack)
                w, h = draw.textsize(str(num), font=font)
                draw.text((8 // 2 - w // 2 , 1), str(num), font=font, fill=textColor)
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

                uuidnum = uuid + str(num)
                
                # save the base POI slightly scaled up for index.md
                
                poiBack.save(os.path.join(papyriOutputPath, uuidnum + ".png"), "png")

                jsonForIndex = {"id": uuidnum, "x": x, "y": z, "placement": "TOP_LEFT", "checkResize": False}
                if jsonForIndex not in poiOverlays:
                    poiOverlays.append(jsonForIndex)

                imgForIndex = '<img class="poiOverlay" id="{uuidnum}" src="../../{uuidnum}.png" title="{title}" alt="{title}">'.format(uuidnum=uuidnum, title=title)
                if imgForIndex not in poiImages:
                    poiImages.append(imgForIndex)

    for banner in banners[d]:
        color = banner["Color"]
        x = banner["Pos"]["X"]
        z = banner["Pos"]["Z"]
        y = banner["Pos"]["Y"]
        coords = "{} {} {}".format(str(x), str(y), str(z))
        name = json.loads(banner.get("Name", '{}')).get("text", "")
        overlayId = name + color + str(x) + str(z)
        poiOverlays.append({"id": overlayId, "x": x, "y": z, "checkResize": False, "placement": "CENTER"})


        bannerImage = PIL.Image.open(os.path.join(templatePath, "{color}banner.png".format(color=color)))
        bannerImage = bannerImage.resize((24, 32))

        poiImage = PIL.Image.new("RGBA", (256, 64), (255, 255, 255, 0))
        if name:
            draw = PIL.ImageDraw.Draw(poiImage)            
            w, h = draw.textsize(name, font=mcfont)
            poiImage = poiImage.resize((w, 64))
            draw = PIL.ImageDraw.Draw(poiImage)            
            textX = 0
            textY = 34
            draw.rectangle((textX, textY, textX + w, textY + h), fill=(0, 0, 0, 192))
            draw.text((textX, textY), name, font=mcfont, fill=(255, 255, 255, 255))
            
            poiImage.paste(bannerImage, (w // 2 - 12, 0))
        else:
            poiImage = poiImage.resize((24, 64))
            poiImage.paste(bannerImage, (0, 0))

            
        imageNameText = color + name
        imageName = hashlib.md5(imageNameText.encode("utf-8")).hexdigest()            
        poiImage.save(os.path.join(papyriOutputPath, imageName + ".png"))


        poiImages.append('<img class="poiOverlay" id="{overlayId}" src="../../{imageName}.png" title="{coords}" alt="{coords}">'.format(imageName=imageName, color=color, overlayId=overlayId, coords=coords))
    
    mapOutputPath = os.path.join(papyriOutputPath, "map", dimDict[d])
    logging.info("Generating index.html file for {}".format(dimDict[d]))
    # put aside some stuff for stuff                                            
    tileSource = []
    for bigMap in mapFileObjsByDim[d].items():
        bigMapName = "{}_{}_{}".format(d, *bigMap[0][0])
        x, y = bigMap[0][0] 


        tileSource.append(dict(tileSource="{}.dzi".format(bigMapName), x=x,
        y=y, width=canvasSize))

    tileSources = "tileSources: " + json.dumps(tileSource, indent=2)          

    index = indexTemplateTop.replace("replaceThisWithTheBackgroundColour", dimColour[d]) + tileSources + ",\n"


    
    index += "overlays: " + json.dumps(poiOverlays, indent=2)

    index += indexTemplateBottom

    
    index += "\n".join(poiImages)

    with open(os.path.join(mapOutputPath, "index.html"), "+w", encoding="utf-8") as outFile:
        outFile.write(index)
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
        poisFile.write("[POI instructions](https://github.com/jason-green-io/papyri/blob/master/README.md#poi-instructions)")








