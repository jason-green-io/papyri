#!/usr/bin/python3
import os
import datetime
import glob
import logging
import pynbt
import bedrock.leveldb as leveldb
from PIL import ImageFont, Image, ImageDraw
import math
import operator
from collections import defaultdict, OrderedDict
from tqdm import tqdm
import argparse
import gzip
import json
import shutil
import re
from io import BytesIO
import sys
import hashlib
import time


mapLinkFormat = "map/{d}/#zoom=0.02&x={x}&y={z}"

filenameFormat = "map_{mapId}_{mapHash}_{epoch}_{dim}_{x}_{z}_{scale}.png"
now = time.time()

multipliers = [180, 220, 255, 135]

colorGradient = ["#ff0000",
                 "#ea0015",
                 "#d4002b",
                 "#bf0040",
                 "#aa0055",
                 "#95006a",
                 "#800080",
                 "#6a0095",
                 "#5500aa",
                 "#4000bf",
                 "#2b00d4",
                 "#1500ea",
                 "#0000ff"]

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

# Setup the logger
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

dimDict = {-1: "nether",
           0: "overworld",
           1: "end"}

regionDict = {"region": 0,
              "DIM1/region": 1,
              "DIM-1/region": -1}


bannersOverlay = []
mapsOverlay = defaultdict(list)


def multiplyColor(colorTuple, multiplier):
    return tuple([math.floor(a * multiplier / 255.0) for a in colorTuple])


allColors = [multiplyColor(color, multiplier)
             for color in basecolors for multiplier in multipliers]


def getidHashes(outputFolder):
    mapPngs = glob.glob(os.path.join(outputFolder, "map_*_*_*_*_*_*_*.png"))
    idHashEpochs = []
    idHashes = OrderedDict()

    for filename in mapPngs:
        filename = filename.split("/")[-1].split("_")
        mapId = filename[1]
        mapHash = filename[2]
        epoch = filename[3]
        idHashEpochs.append((mapId, mapHash, epoch))

    idHashEpochs.sort(key=operator.itemgetter(2))
    [print(a) for a in idHashEpochs]
    for idHashEpoch in idHashEpochs:
        idHashes[idHashEpoch[0]] = idHashEpoch[1]
    [print(a) for a in idHashes.items()]
    return idHashes

def makeMapPngBedrock(worldFolder, outputFolder, unlimitedTracking=False):

    os.makedirs(outputFolder, exist_ok=True)

    idHashes = getidHashes(outputFolder)


    db = leveldb.open(os.path.join(worldFolder, "db"))
    for a in tqdm(leveldb.iterate(db)):
        key = bytearray(a[0])
        if b"map" in key:
            mapNbtIo = BytesIO(a[1])
            mapNbt = pynbt.NBTFile(io=mapNbtIo, little_endian=True)

            try:
                mapUnlimitedTracking = mapNbt["unlimitedTracking"].value
            except KeyError:
                mapUnlimitedTracking = False

            if mapUnlimitedTracking and not unlimitedTracking:
                continue
            mapId = mapNbt["mapId"].value
            mapScale = mapNbt["scale"].value
            mapTime = now
            mapX = mapNbt["xCenter"].value
            mapZ = mapNbt["zCenter"].value
            mapDim = mapNbt["dimension"].value
            mapColors = mapNbt["colors"].value
            try:
                banners = mapNbt["banners"]
            except KeyError:
                banners = []
            for banner in banners:
                X = banner["Pos"]["X"].value
                Y = banner["Pos"]["Y"].value
                Z = banner["Pos"]["Z"].value
                Color = banner["Color"].value
                try:
                    Name = json.loads(banner["Name"].value)["text"]

                except KeyError:
                    Name = ""
                bannersOverlay.append({"X": X,
                                       "Y": Y,
                                       "Z": Z,
                                       "Color": Color,
                                       "Name": Name,
                                       "Dimension": dimDict[mapDim]})
            mapImage = Image.frombytes("RGBA", (128, 128),
                                       bytes([x % 256 for x in mapColors]),
                                       'raw')
            imageHash = hashlib.md5(mapImage.tobytes()).hexdigest()

            if (str(mapId), imageHash) not in idHashes.items() and imageHash != "fcd6bcb56c1689fcef28b57c22475bad":
                filename = filenameFormat.format(mapId=mapId,
                                                 mapHash=imageHash,
                                                 epoch=mapTime,
                                                 scale=mapScale,
                                                 x=mapX,
                                                 z=mapZ,
                                                 dim=mapDim)
                mapImage = mapImage.resize((128 * 2 ** mapScale,) * 2)
                # print(mapImage.size)

                mapImage.save(os.path.join(outputFolder, filename))
                mapImage.close()


def makeMapPngJava(worldFolder, outputFolder, unlimitedTracking=False):
    mapDatFiles = glob.glob(os.path.join(worldFolder, "data/map_*.dat"))
    os.makedirs(outputFolder, exist_ok=True)

    idHashes = getidHashes(outputFolder)

    for mapDatFile in tqdm(mapDatFiles, "map_*.dat nbt -> png"):
        mapNbt = pynbt.NBTFile(io=gzip.open(mapDatFile))
        # print(mapDict["data"].keys())
        try:
            mapUnlimitedTracking = mapNbt["data"]["unlimitedTracking"].value
        except KeyError:
            mapUnlimitedTracking = False

        if mapUnlimitedTracking and not unlimitedTracking:
            continue
        mapId = os.path.basename(mapDatFile).strip("map_").strip(".dat")
        mapScale = mapNbt["data"]["scale"].value
        mapX = mapNbt["data"]["xCenter"].value
        mapZ = mapNbt["data"]["zCenter"].value
        mapDim = mapNbt["data"]["dimension"].value
        mapColors = mapNbt["data"]["colors"].value
        colorTuples = [allColors[x % 256] for x in mapColors]
        try:
            banners = mapNbt["data"]["banners"]
        except KeyError:
            banners = []
        for banner in banners:
            X = banner["Pos"]["X"].value
            Y = banner["Pos"]["Y"].value
            Z = banner["Pos"]["Z"].value
            Color = banner["Color"].value
            try:
                Name = json.loads(banner["Name"].value)["text"]

            except KeyError:
                Name = ""
            bannersOverlay.append({"X": X,
                                   "Y": Y,
                                   "Z": Z,
                                   "Color": Color,
                                   "Name": Name,
                                   "Dimension": dimDict[mapDim]})
        mapImage = Image.new("RGBA", (128, 128))
        mapImage.putdata(colorTuples)
        imageHash = hashlib.md5(mapImage.tobytes()).hexdigest()

        if str(mapId) not in idHashes.keys():

            mapTime = os.path.getmtime(mapDatFile)
        else:
            mapTime = now

        if (str(mapId), imageHash) not in idHashes.items() and imageHash != "fcd6bcb56c1689fcef28b57c22475bad":
            mapImage = mapImage.resize((128 * 2 ** mapScale,) * 2)
            filename = filenameFormat.format(mapId=mapId,
                                             mapHash=imageHash,
                                             epoch=mapTime,
                                             scale=mapScale,
                                             x=mapX,
                                             z=mapZ,
                                             dim=mapDim)

            mapImage.save(os.path.join(outputFolder, filename))
            mapImage.close()


def mergeToLevel4(mapPngFolder, outputFolder):
    filenameFormat = "merged_map_{dim}_{x}_{z}.png"
    os.makedirs(outputFolder, exist_ok=True)
    level4Dict = defaultdict(lambda: defaultdict(list))
    mapPngs = glob.glob(os.path.join(mapPngFolder, "map_*_*_*_*_*_*_*.png"))
    for mapPng in mapPngs:
        name = os.path.basename(mapPng)
        (mapId,
         mapHash,
         epoch,
         dim,
         x,
         z,
         scale) = name.strip("map_").strip(".png").split("_")

        x = int(x)
        z = int(z)
        scale = int(scale)
        dim = int(dim)
        mapId = int(mapId)
        epoch = float(epoch)
        mapTopLeft = (x - 128 * 2 ** scale //
                      2 + 64, z - 128 * 2 ** scale // 2 + 64)
        mapTuple = (name, mapId, epoch, dim, mapTopLeft, scale)
        level4Coords = (mapTopLeft[0] // 2048 * 2048,
                        mapTopLeft[1] // 2048 * 2048)
        level4Dict[dim][level4Coords].append(mapTuple)
    """
    mapPngList.sort(key=operator.itemgetter(2))
    mapPngList.sort(key=operator.itemgetter(1))
    mapPngList.sort(key=operator.itemgetter(6), reverse=True)
    """
    for dim in level4Dict.items():
        d = dim[0]
        for coords in tqdm(dim[1].items(), "level 4 of dim: {}".format(d)):
            c = coords[0]
            coords[1].sort(key=operator.itemgetter(1))
            coords[1].sort(key=operator.itemgetter(2))
            coords[1].sort(key=operator.itemgetter(5), reverse=True)
            level4MapPng = Image.new("RGBA", (2048, 2048))
            for mapTuple in coords[1]:
                mapPngCoords = (divmod(mapTuple[4][0], 2048)[1],
                                divmod(mapTuple[4][1], 2048)[1])
                with Image.open(os.path.join(mapPngFolder, mapTuple[0])) as mapPng:
                    level4MapPng.paste(mapPng, mapPngCoords, mapPng)
                #print(mapTuple)

            fileName = filenameFormat.format(dim=d, x=c[0], z=c[1]*-1)

            filePath = os.path.join(outputFolder, fileName)
            level4MapPng.save(filePath)
            level4MapPng.close()

def genZoom17Tiles(level4MapFolder, outputFolder):
    level4MapFilenames = glob.glob(os.path.join(level4MapFolder, "merged_map_*_*_*.png"))
    for level4MapFilename in tqdm(level4MapFilenames, "level 4 -> zoom 17 tiles"):
        name = os.path.basename(level4MapFilename)
        dim, x, z = name.strip("merged_map_").strip(".png").split("_")
        level4x = int(x)
        level4z = int(z)
        tilex = level4x // 2048
        tilez = level4z // 2048 * -1
        with Image.open(level4MapFilename) as level4MapPng:
            for zoom in range(17, 18):
                numTiles = 2 ** (zoom - 13)
                imageWidth = 2048 // numTiles
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
                        tilePng = tilePng.resize((256, 256))
                        tilePng.save(filename)

def extrapolateZoom(tileFolder, level):
    zoom17Filenames = glob.glob(os.path.join(tileFolder, "*/{}/*/*.png".format(level + 1)))
    newZoomDict = defaultdict(list)
    for filename in zoom17Filenames:
        dim, zoom, x, y = filename.strip(tileFolder).strip(".png").split("/")
        x = int(x)
        y = int(y)
        xnew, xq = divmod(x, 2)
        ynew, yq = divmod(y, 2)
        newZoomDict[(dim, xnew, ynew)].append((xq, yq, filename))
    for newTile in tqdm(newZoomDict.items(), "zoom {} tiles".format(level)):
        foldername = os.path.join(tileFolder, "{}/{}/{}".format(newTile[0][0], level, newTile[0][1]))
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


def genBanners(bannerTupleList, outputFolder):
    bannerJson = []
    os.makedirs(outputFolder, exist_ok=True)
    for d, banners in tqdm(bannerTupleList.items()):
        for banner in tqdm(banners, "Generating banners"):

            coords = "{} {} {}".format(str(banner["X"]),
                                       str(banner["Y"]),
                                       str(banner["Z"]))

            name = re.subn("\[(.*?)\]", r"[\1](#\1)", banner["Name"])[0]

            POI = {"title": banner["Name"],
                   "x": banner["X"],
                   "z": banner["Z"],
                   "color": banner["Color"],
                   "d": d,
                   "maplink": mapLinkFormat.format(x=banner["X"],
                                                   y=banner["Y"],
                                                   z=banner["Z"],
                                                   d=d)}

            #logging.info(POI)

            bannerJson.append(POI)


            #poiOverlays.add(poiOverlay(overlayId, x, z, False, "CENTER"))


            bannerImage = Image.open(os.path.join("template", "banners-template", "{color}banner.png".format(color=banner["Color"])))

            poiImage = Image.new("RGBA", (256, 64), (255, 255, 255, 0))
            if banner["Name"]:
                draw = ImageDraw.Draw(poiImage)
                w, h = draw.textsize(banner["Name"], font=font)
                #poiImage = poiImage.resize((w, 64))
                draw = ImageDraw.Draw(poiImage)
                textX = 127 - (w // 2)
                textY = 34
                draw.rectangle((textX, textY, textX + w, textY + h), fill=(0, 0, 0, 160))
                draw.text((textX, textY), banner["Name"], font=font, fill=(255, 255, 255, 255))

                poiImage.paste(bannerImage, (127 - 12, 0))
            else:
                #poiImage = poiImage.resize((24, 64))
                poiImage.paste(bannerImage, (127 - 12, 0))


            poiImage.save(os.path.join(outputFolder, banner["overlayId"] + ".png"))

            #poiImages.append(dict(h=64, w=256, id=overlayId, src="../../{imageName}".format(imageName), title=coords, alt=coords))

def genBannerMarkers(bannerList, outputFolder):

    with open(os.path.join(outputFolder, "banners.json"), "+w", encoding="utf-8") as f:
        f.write(json.dumps(bannerList))


def getMcaFiles(worldFolder):
    mcaList = []
    for dim in regionDict.items():
        mcaFiles = glob.glob(os.path.join(worldFolder, dim[0], "*.mca" ))
        for mcaFile in mcaFiles:
            age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.stat(mcaFile).st_mtime)
            name = mcaFile.rsplit("/")[-1]
            mca = {"name": name, "age": age.days, "dim": dim[1]}
            mcaList.append(mca)
            print(mca)
    return mcaList





def genMcaMarkers(mcaFileList, outputFolder):
    mcaList = []
    for mcaFile in mcaFileList:
        Xregion, Zregion = mcaFile["name"].split(".")[1:3]
        print(Xregion,Zregion)
        X = int(Xregion) * 512
        Z = int(Zregion) * 512
        latlngs = [[Z, X], [Z + 511, X + 511]]
        age = mcaFile["age"]
        if age >= 128:
            color = "black"
        else:
            color = colorGradient[int(age / 128 * 13)]
        mca = {"Dimension": dimDict[mcaFile["dim"]], "latlngs": latlngs, "Color": color}
        mcaList.append(mca)

    with open(os.path.join(outputFolder, "mca.json"), "+w", encoding="utf-8") as f:
        f.write(json.dumps(mcaList))


def copyAssets(outputFolder):
    if not os.path.isdir(os.path.join(outputFolder, "assets")):
        logging.info("Assets folder not found, copying to %s", outputFolder)
        shutil.copytree("./template/assets", os.path.join(outputFolder, "assets"))
        shutil.copyfile("./template/index.html", os.path.join(outputFolder))

    else:
        logging.info("Assets folder found")

def main():
    parser = argparse.ArgumentParser(description='convert minecraft maps to the web')
    parser.add_argument('--world', help="world folder or save folder (this is the folder level.dat is in)", required=True)
    parser.add_argument('--includeunlimitedtracking', help="include maps that have unlimited tracking on, this includes older maps from previous Minecraft versions and treasure maps in +1.13", action="store_true")
    parser.add_argument('--output', help="output path for web stuff", required=True)
    parser.add_argument("--sortmaps", default="time", choices=["time", "id"], help="sort maps by last modified or by id (if they were copied and the file metadata is gone)")
    parser.add_argument("--overlayplayers", action='store_true', help="show last known player locations")

    # get the args
    args = parser.parse_args()

    mapsOutput = os.path.join(args.output, "maps")
    tileOutput = os.path.join(args.output, "tiles")
    mergedMapsOutput = os.path.join(args.output, "merged-maps")
    #bannersOutput = os.path.join(args.output, "banners")
    if os.path.isdir(os.path.join(args.world, "db")):
        makeMapPngBedrock(args.world, mapsOutput, unlimitedTracking=args.includeunlimitedtracking)
    elif os.path.isdir(os.path.join(args.world, "data")):
        makeMapPngJava(args.world, mapsOutput, unlimitedTracking=args.includeunlimitedtracking)
        mcaFilesList = getMcaFiles(args.world)
        genMcaMarkers(mcaFilesList, args.output)
    else:
        logging.info("Map data not found in %s", args.output)
        sys.exit(1)

    mergeToLevel4(mapsOutput, mergedMapsOutput)
    genZoom17Tiles(mergedMapsOutput, tileOutput)
    for zoom in range(16, -1, -1):
        extrapolateZoom(tileOutput, zoom)
    #genBanners(bannersOverlay, bannersOutput)
    genBannerMarkers(bannersOverlay, args.output)
    copyAssets(args.output)
    logging.info("Done")


if __name__ == "__main__":
    main()
