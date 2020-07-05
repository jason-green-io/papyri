#!/usr/bin/python3
import os
import datetime
import glob
import logging
import nbtlib
import bedrock.leveldb as leveldb
from PIL import ImageFont, Image, ImageDraw
import math
import operator
from collections.abc import Callable
from collections import defaultdict, OrderedDict, namedtuple
from tqdm import tqdm
import argparse
import gzip
import json
import distutils.dir_util
import re
from io import BytesIO
import sys
import hashlib
import time
import struct
import numpy as np

__author__ = "Jason Green"
__copyright__ = "Copyright 2020, Tesseract Designs"
__credits__ = ["Jason Green"]
__license__ = "MIT"
__version__ = "1.0.1"
__maintainer__ = "Jason Green"
__email__ = "jason@green.io"
__status__ = "release"

dir_path = os.path.dirname(os.path.realpath(__file__))

# filename format for map .dat file  color data
filenameFormat = "map_{mapId}_{mapHash}_{epoch}_{dim}_{x}_{z}_{scale}.png"

# now in epoch
now = time.time()

# setup the logger
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

# stuff to convert the map color data to RGB values
multipliers = [180, 220, 255, 135]

# this is base pallette Minecraft uses, used with the multipliers
basecolors = [(0, 0, 0, 0),
              (127, 178, 56),
              (247, 233, 163),
              (199, 199, 199),
              (255, 0, 0),
              (160, 160, 255),
              (167, 167, 167),
              (0, 124, 0),
              (255, 255, 255),
              (164, 168, 184),
              (151, 109, 77),
              (112, 112, 112),
              (64, 64, 255),
              (143, 119, 72),
              (255, 252, 245),
              (216, 127, 51),
              (178, 76, 216),
              (102, 153, 216),
              (229, 229, 51),
              (127, 204, 25),
              (242, 127, 165),
              (76, 76, 76),
              (153, 153, 153),
              (76, 127, 153),
              (127, 63, 178),
              (51, 76, 178),
              (102, 76, 51),
              (102, 127, 51),
              (153, 51, 51),
              (25, 25, 25),
              (250, 238, 77),
              (92, 219, 213),
              (74, 128, 255),
              (0, 217, 58),
              (129, 86, 49),
              (112, 2, 0),
              (209, 177, 161),
              (159, 82, 36),
              (149, 87, 108),
              (112, 108, 138),
              (186, 133, 36),
              (103, 117, 53),
              (160, 77, 78),
              (57, 41, 35),
              (135, 107, 98),
              (87, 92, 92),
              (122, 73, 88),
              (76, 62, 92),
              (76, 50, 35),
              (76, 82, 42),
              (142, 60, 46),
              (37, 22, 16)]


def multiplyColor(colorTuple, multiplier):
    "calculates final color values using multiplier"
    return tuple([math.floor(a * multiplier / 255.0) for a in colorTuple])


# this a list of all possible colors a pixel can be on a map
allColors = [multiplyColor(color, multiplier)
             for color in basecolors for multiplier in multipliers]

# convert dimension names to/from human readable
dimDict = {"-1": "nether",
           "0": "overworld",
           "1": "end",
           "minecraft:overworld": "0",
           "minecraft:nether": "1",
           "minecraft:end": "-1",
           "nether": "-1",
           "overworld": "0",
           "end": "1"}


def scaleImage(image, factor):
    a = np.array(image)

    #logging.info("Scaling %s %s new %s %s factor %s", W, H, newW, newH, factor)
    b = a.repeat(factor,axis=0).repeat(factor,axis=1)
    return Image.fromarray(b)



def findMapFiles(inputFolder):
    mapFiles = []
    
    folderTree = list(os.walk(inputFolder))
    
    dataFolders = [f for f in folderTree if f[0].endswith(os.sep + "data")]
    
    for folder in dataFolders:
        maybeMapFiles = [os.path.join(folder[0], f) for f in folder[2] if f.startswith("map_") and f.endswith(".dat")]
        if "idcounts.dat" in folder[2]:
            logging.info("Found %s maps in %s", len(maybeMapFiles), folder[0])
            mapFiles = maybeMapFiles
    
    
    if not mapFiles:
        logging.info("Didn't find any maps, did you specify the correct world location?")
        sys.exit(1)
    
    return mapFiles


class LastUpdatedOrderedDict(OrderedDict):
    'Store items in the order the keys were last added'
    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        OrderedDict.__setitem__(self, key, value)


class DefaultOrderedDict(OrderedDict):
    "Source: http://stackoverflow.com/a/6190500/562769"
    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and
           not isinstance(default_factory, Callable)):
            raise TypeError('first argument must be callable')
        OrderedDict.__init__(self, *a, **kw)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return OrderedDict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
        return type(self), args, None, None, self.items()

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))

    def __repr__(self):
        return 'OrderedDefaultDict(%s, %s)' % (self.default_factory,
                                               OrderedDict.__repr__(self))


# all the banners
banners = set()

# all the maps
maps = DefaultOrderedDict(LastUpdatedOrderedDict)

# couple of structures to keep stuff
BannerTuple = namedtuple("BannerTuple", ["X", "Y", "Z", "name", "dimension", "color"])
MapTuple = namedtuple("MapTuple", ["name", "mapId", "epoch", "dimension", "mapTopLeft", "scale"])

def getidHashes(outputFolder):
    """Returns a dict of {latest updated map ID: hash}"""

    # get all generated maps
    mapPngs = glob.glob(os.path.join(outputFolder, "map_*_*_*_*_*_*_*.png"))
    
    idHashEpochs = []
    idHashes = OrderedDict()

    for filename in mapPngs:
        filename = os.path.split(filename)[-1].split("_")
        mapId = filename[1]
        mapHash = filename[2]
        epoch = float(filename[3])
        idHashEpochs.append((mapId, mapHash, epoch))
    
    # sort the whole thing by epoch
    idHashEpochs.sort(key=operator.itemgetter(2))

    for idHashEpoch in idHashEpochs:
        # this will only keep the latest map ids around for rendering
        idHashes[idHashEpoch[0]] = idHashEpoch[1]
    
    return idHashes


def makeMapPngBedrock(worldFolder, outputFolder, unlimitedTracking=False):
    """generate all the png files from leveldb"""

    # mke sure the output exsists
    os.makedirs(outputFolder, exist_ok=True)
    
    # get the current map data hashes
    idHashes = getidHashes(outputFolder)

    # open leveldb
    db = leveldb.open(os.path.join(worldFolder, "db"))

    # iterate over all the maps
    for a in tqdm(leveldb.iterate(db), bar_format="{l_bar}{bar}"):
        key = bytearray(a[0])
        if b"map" in key:
            # get extract an nbt object
            mapNbtIo = BytesIO(a[1])
            mapNbtFile = nbtlib.File.parse(mapNbtIo, byteorder="little")
            mapNbt = mapNbtFile.root
            # print(mapNbt)
            
            # is the map unlimitedTracking?
            try:
                mapUnlimitedTracking = mapNbt["unlimitedTracking"]
            except KeyError:
                mapUnlimitedTracking = False

            # skip if we didn't specify to include then on the cli
            if mapUnlimitedTracking and not unlimitedTracking:
                continue
            
            # assign a bunch of stuff
            mapId = int(mapNbt["mapId"])
            mapScale = int(mapNbt["scale"])
            mapTime = now
            mapX = int(mapNbt["xCenter"])
            mapZ = int(mapNbt["zCenter"])
            mapDim = str(mapNbt["dimension"])
            mapColors = mapNbt["colors"]

            # got banners?
            try:
                banners = mapNbt["banners"]
            except KeyError:
                banners = []

            # iterate over them
            for banner in banners:
                # more assigning
                X = banner["Pos"]["X"]
                Y = banner["Pos"]["Y"]
                Z = banner["Pos"]["Z"]
                color = banner["Color"]
                dim = dimDict[mapDim]
            
                try:
                    name = json.loads(banner["Name"])["text"]
                except KeyError:
                    name = ""

                bannerDict = {"X": X,
                              "Y": Y,
                              "Z": Z,
                              "color": color,
                              "name": name,
                              "dimension": dim}

                # buils a tuple and store it
                bannerTuple = BannerTuple(**bannerDict)
                banners.add(bannerTuple)

            # create an image from the color data
            mapImage = Image.frombytes("RGBA", (128, 128),
                                       bytes([x % 256 for x in mapColors]),
                                       'raw')
            # compute a hash of the data
            imageHash = hashlib.md5(mapImage.tobytes()).hexdigest()

            # if we've never seen this data on this map id, then write out the
            # file
            if (str(mapId), imageHash) not in idHashes.items() and imageHash != "fcd6bcb56c1689fcef28b57c22475bad":
                filename = filenameFormat.format(mapId=mapId,
                                                 mapHash=imageHash,
                                                 epoch=mapTime,
                                                 scale=mapScale,
                                                 x=mapX,
                                                 z=mapZ,
                                                 dim=mapDim)
                # scale the image based on the map zoom level
                mapImage = scaleImage(mapImage, 2 ** mapScale)
                # print(mapImage.size)
                # save and close
                mapImage.save(os.path.join(outputFolder, filename))
                mapImage.close()


def makeMapPngJava(mapDatFiles, outputFolder, unlimitedTracking=False):
    """generate png from map*.dat files"""
    
    os.makedirs(outputFolder, exist_ok=True)

    idHashes = getidHashes(outputFolder)

    for mapDatFile in tqdm(mapDatFiles, "map_*.dat nbt -> png".ljust(24), bar_format="{l_bar}{bar}"):
        mapNbtFile = nbtlib.load(mapDatFile)
        mapNbt = mapNbtFile.root
        # print(mapNbt["data"])
        try:
            mapUnlimitedTracking = mapNbt["data"]["unlimitedTracking"]
        except KeyError:
            mapUnlimitedTracking = False

        if mapUnlimitedTracking and not unlimitedTracking:
            continue
        mapId = os.path.basename(mapDatFile).strip("map_").strip(".dat")
        mapScale = int(mapNbt["data"]["scale"])
        mapX = int(mapNbt["data"]["xCenter"])
        mapZ = int(mapNbt["data"]["zCenter"])
        mapDim = str(mapNbt["data"]["dimension"])
        mapColors = mapNbt["data"]["colors"]
        colorTuples = [allColors[x % 256] for x in mapColors]

        try:
            mapBanners = mapNbt["data"]["banners"]
            # print(banners)
        except KeyError:
            mapBanners = []
        for banner in mapBanners:
            # print(banner)
            X = int(banner["Pos"]["X"])
            Y = int(banner["Pos"]["Y"])
            Z = int(banner["Pos"]["Z"])
            color = banner["Color"]
            dim = str(dimDict[mapDim])
            try:
                name = json.loads(banner["Name"])["text"]

            except KeyError:
                name = ""
            bannerDict = {"X": X,
                          "Y": Y,
                          "Z": Z,
                          "color": color,
                          "name": name,
                          "dimension": dim}
            bannerTuple = BannerTuple(**bannerDict)
            banners.add(bannerTuple)
        mapImage = Image.new("RGBA", (128, 128))
        mapImage.putdata(colorTuples)
        imageHash = hashlib.md5(mapImage.tobytes()).hexdigest()

        if str(mapId) not in idHashes.keys():

            mapTime = os.path.getmtime(mapDatFile)
        else:
            mapTime = now

        if (str(mapId), imageHash) not in idHashes.items() and imageHash != "fcd6bcb56c1689fcef28b57c22475bad":
            mapImage = scaleImage(mapImage, 2 ** mapScale)
            filename = filenameFormat.format(mapId=mapId,
                                             mapHash=imageHash,
                                             epoch=mapTime,
                                             scale=mapScale,
                                             x=mapX,
                                             z=mapZ,
                                             dim=mapDim)

            mapImage.save(os.path.join(outputFolder, filename))
            mapImage.close()

    logging.info("Found %s banners", len(banners))


def mergeToLevel4(mapPngFolder, outputFolder):
    """pastes all maps to render onto a intermediate zoom level 4 map"""
    # what are we calling these crazy things
    filenameFormat = "merged_map_{dim}_{x}_{z}.png"
    
    # make sure the output exsists
    os.makedirs(outputFolder, exist_ok=True)

    # this will hold all the maps, by dimension and associated zoom level 4 map
    level4Dict = defaultdict(lambda: defaultdict(list))

    # get all the maps
    mapPngs = glob.glob(os.path.join(mapPngFolder, "map_*_*_*_*_*_*_*.png"))
    
    # iterate over all the maps
    for mapPng in mapPngs:
        name = os.path.basename(mapPng)
        (mapId,
         mapHash,
         epoch,
         dim,
         x,
         z,
         scale) = name.strip("map_").strip(".png").split("_")
        # change some types
        x = int(x)
        z = int(z)
        scale = int(scale)
        dim = int(dim)
        mapId = int(mapId)
        if not dim in dimDict:
            logging.info("Skipped map %s with invalid dimension.", mapId)
            continue
        epoch = float(epoch)
        
        # convert the center of the map to the top left corner
        mapTopLeft = (x - 128 * 2 ** scale //
                      2 + 64, z - 128 * 2 ** scale // 2 + 64)
        # make a tuple out of it
        amap = MapTuple(name=name, mapId=mapId, epoch=epoch, dimension=dim, mapTopLeft=mapTopLeft, scale=scale)
        # figure out which level 4 map it belongs to
        level4Coords = (mapTopLeft[0] // 2048 * 2048,
                        mapTopLeft[1] // 2048 * 2048)
        # throw it into a "dict"
        level4Dict[dim][level4Coords].append(amap)
    
    # iterate over the level 4 buckets
    for dim in level4Dict.items():
        d = dim[0]
        for coords in tqdm(dim[1].items(), "level 4 of dim: {}".format(d).ljust(24), bar_format="{l_bar}{bar}"):
            c = coords[0]
            
            mapTuples = coords[1]
            
            # sort them, import for the rendering order
            mapTuples.sort(key=lambda x: x.mapId)
            mapTuples.sort(key=lambda x: x.epoch)
            mapTuples.sort(key=lambda x: x.scale, reverse=True)
            
            # create the level 4 images
            level4MapPng = Image.new("RGBA", (2048, 2048))
            
            # iterate over the maps in each bucket
            for mapTuple in mapTuples:
                # get the map details
                maps[(mapTuple.dimension, mapTuple.scale,
                      mapTuple.mapTopLeft[0],
                      mapTuple.mapTopLeft[1])].update({mapTuple.mapId: None})
                mapPngCoords = (divmod(mapTuple.mapTopLeft[0], 2048)[1],
                                divmod(mapTuple.mapTopLeft[1], 2048)[1])
                # paste the image into the level 4 map
                with Image.open(os.path.join(mapPngFolder, mapTuple.name)) as mapPng:
                    level4MapPng.paste(mapPng, mapPngCoords, mapPng)
                #print(mapTuple)
            # figure out the name of the file, and save it
            fileName = filenameFormat.format(dim=d, x=c[0], z=c[1]*-1)

            filePath = os.path.join(outputFolder, fileName)
            level4MapPng.save(filePath)
            level4MapPng.close()


def genZoom17Tiles(level4MapFolder, outputFolder):
    """generates lowest zoom level tiles from zcombined oom level 4 maps"""

    # get all the level 4 maps 
    level4MapFilenames = glob.glob(os.path.join(level4MapFolder, "merged_map_*_*_*.png"))
    # iterate over level4 maps
    for level4MapFilename in tqdm(level4MapFilenames, "level 4 -> zoom 17 tiles", bar_format="{l_bar}{bar}"):
        # get some details
        name = os.path.basename(level4MapFilename)
        dim, x, z = name.strip("merged_map_").strip(".png").split("_")
        level4x = int(x)
        level4z = int(z)
        tilex = level4x // 2048
        tilez = level4z // 2048 * -1
        # open the level 4 map
        with Image.open(level4MapFilename) as level4MapPng:
            # this is pretty useless
            for zoom in range(17, 18):
                numTiles = 2 ** (zoom - 13)
                imageWidth = 2048 // numTiles
                # do math
                for numx in range(numTiles):
                    levelNumx = tilex * numTiles + numx
                    foldername = os.path.join(outputFolder, dim, str(zoom), str(levelNumx))
                    os.makedirs(foldername, exist_ok=True)
                    for numz in range(numTiles):
                        levelNumz = tilez * numTiles + numz
                        cropBox = (numx * imageWidth,
                                numz * imageWidth,
                                numx * imageWidth + imageWidth,
                                numz * imageWidth + imageWidth)
                        filename = os.path.join(foldername, str(levelNumz) + ".png")
                        #print(filename, cropBox )
                        tilePng = level4MapPng.crop(cropBox)
                        tilePng = scaleImage(tilePng, 2)
                        tilePng.save(filename)


def extrapolateZoom(tileFolder, level):
    zoom17Filenames = glob.glob(os.path.join(tileFolder, "*", str(level + 1), "*", "*.png"))
    newZoomDict = defaultdict(list)
    for filename in zoom17Filenames:
        tilePath = os.path.relpath(filename, tileFolder)
        dim, zoom, x, y = tilePath.strip(".png").split(os.sep)
        x = int(x)
        y = int(y)
        xnew, xq = divmod(x, 2)
        ynew, yq = divmod(y, 2)
        newZoomDict[(dim, xnew, ynew)].append((xq, yq, filename))
    for newTile in tqdm(newZoomDict.items(), "zoom {} tiles".format(level).ljust(24), bar_format="{l_bar}{bar}"):
        foldername = os.path.join(tileFolder, str(newTile[0][0]), str(level), str(newTile[0][1]))
        tilePng = Image.new("RGBA", (512,512))
        for previousTile in newTile[1]:
            topLeft = (previousTile[0] * 256, previousTile[1] * 256)
            previousTilePng = Image.open(previousTile[2])
            tilePng.paste(previousTilePng, topLeft, previousTilePng)
            #print(previousTile)
        #print(filename)
        tilePng = tilePng.resize((256,256))
        os.makedirs(foldername, exist_ok=True)
        tilePng.save(os.path.join(foldername, "{}.png".format(newTile[0][2])))


def genBannerMarkers(bannerList, outputFolder):
    """generate the banner.json file fram the banner list"""
    with open(os.path.join(outputFolder, "banners.json"), "+w", encoding="utf-8") as f:
        bannerList = [a._asdict() for a in bannerList]
        f.write(json.dumps(list(bannerList)))


def genMapIdMarkers(maps, outputFolder):
    mapsList = []

    for amap in maps.items():
        X = amap[0][2] - 64
        Z = amap[0][3] - 64
        
        scale = amap[0][1]
        width = 128 * 2 ** scale
        dimension = amap[0][0] 
        TL = [X, Z]
        TR = [X, Z + width]
        BL = [X + width, Z + width]
        BR = [X + width, Z]

        coordinates = [[TL, TR, BL, BR, TL]]
        properties = {"scale": scale,
                      "dimension": dimDict[dimension],
                      "IDs": ",".join([str(x) for x in amap[1].keys()]) }
        
        geometry = {"type": "Polygon",
                    "coordinates": coordinates}
        
        feature = {"type": "Feature",
                   "properties": properties,
                   "geometry": geometry}
        
        mapsList.append(feature)
    with open(os.path.join(outputFolder, "maps.json"), "+w", encoding="utf-8") as f:
        f.write(json.dumps(mapsList))


def copyTemplate(outputFolder, copytemplate):
    if not os.path.isdir(os.path.join(outputFolder, "assets")) or copytemplate:
        logging.info("Copying template to %s", outputFolder)
        distutils.dir_util.copy_tree(os.path.join(dir_path, "template"), outputFolder)

    else:
        logging.info("Assets folder found, not copying template")


def main():
    parser = argparse.ArgumentParser(description='convert minecraft maps to the web')
    parser.add_argument('--world', help="location of your world folder or save folder", required=True)
    parser.add_argument('--includeunlimitedtracking', help="include maps that have unlimited tracking on, this includes older maps from previous Minecraft versions and treasure maps in +1.13", action="store_true")
    #parser.add_argument('--overlaymca', help="generate the regionfile overlay (Java only)", action="store_true")
    parser.add_argument('--output', help="output path for web stuff", required=True)
    parser.add_argument('--copytemplate', help="copy default index.html and assets (do this if a new release changes the tempalte)", action="store_true")

    # get the args
    args = parser.parse_args()

    # where to the maps go?
    mapsOutput = os.path.join(args.output, "maps")

    # where to the tiles go?
    tileOutput = os.path.join(args.output, "tiles")
    
    # where to the merged zoom level 4 maps go?
    mergedMapsOutput = os.path.join(args.output, "merged-maps")
 
    # figure out if the input folder is java or bedrock
    if os.path.isdir(os.path.join(args.world, "db")):
        # do the bedrock thing
        makeMapPngBedrock(args.world, mapsOutput, unlimitedTracking=args.includeunlimitedtracking)
    else:
        # do the java thing, including generating extra json files for the markers
        mapFiles = findMapFiles(args.world)
        makeMapPngJava(mapFiles, mapsOutput, unlimitedTracking=args.includeunlimitedtracking)
        #if args.overlaymca:
        #    mcaFilesList = getMcaFiles(dataDict["regions"])
        #    keepMcaFiles = genKeepMcaFiles(banners)
        #    genRegionMarkers(mcaFilesList, args.output, keepMcaFiles)
    
    # make the level 4 maps
    mergeToLevel4(mapsOutput, mergedMapsOutput)

    # create the tiles for the lowest zoom level
    genZoom17Tiles(mergedMapsOutput, tileOutput)

    # generate the rest of the zoom levels from level 17
    for zoom in range(16, -1, -1):
        extrapolateZoom(tileOutput, zoom)
    
    # make the banner markers
    genBannerMarkers(banners, args.output)

    # make the maps info markers
    genMapIdMarkers(maps, args.output)
    
    # make sure the html and assets are present and copied
    copyTemplate(args.output, args.copytemplate)
    
    logging.info("Done")


if __name__ == "__main__":
    main()
