# papyri version 1.0

Papyri is a Minecraft map item web presenter. It will show all maps and banners created on a server positioned and scaled properly, creating a mosaic of your world as explored with maps. Since many maps can be created of the same area, Papyri will prioritize rendering so that maps with higher detail are rendered on top of maps of lower detail and maps at the same detail are rendered in order from oldest updated to newest updated.

[Example 1 - Byblos](https://minecraft.greener.ca/byblos/)

![screen shot 2018-03-07 at 9 32 56 pm](https://user-images.githubusercontent.com/2853489/37129992-952c8bac-224f-11e8-95ce-21a59954409d.png)

## prerequisites

python3 and pip (pip3) (Not tested in python2)


some python stuff you'll need:

    pip3 tqdm install libnbt Pillow

## usage

```
usage: papyri.py [-h] [--poi] [--banners] --mcdata MCDATA --output OUTPUT
                 [--zoomlevel {4,5,6,7,8}] [--overlay] [--nostitch]
                 [--mapstats]

convert minecraft maps to the web

optional arguments:
  -h, --help            show this help message and exit
  --poi                 generate POI file and show POI books, this outputs
                        papyri.md that can be used with
                        http://dynalon.github.io/mdwiki/#!index.md to show on
                        the web
  --banners             generate POI file and show banners, this outputs
                        papyri.md that can be used with
                        http://dynalon.github.io/mdwiki/#!index.md to show on
                        the web
  --mcdata MCDATA       input path to minecraft server data
  --output OUTPUT       output path for web stuff
  --zoomlevel {4,5,6,7,8}
                        size of maps generated in mc zoom levels, 8 = 65k, 7 =
                        32k
  --overlay             add overlay showing map IDs
  --nostitch            disable generating the map, useful if you only want
                        the overlay displayed
```

Once it's done, the contents of the output folder can be served as a website. It's completely static so it can be put in an S3 bucket a github project or hosted locally on your machine by running something like `python3 -m SimpleHTTPServer` inside the output folder.


This project is licensed under the terms of the MIT license.
