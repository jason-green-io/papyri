# papyri version 0.5

Papyri is a Minecraft map item web presenter. It will show all maps created on a server positioned and scaled properly, creating a mosaic of your world as explored with maps. Since Many maps can be created of the same area, Papyri will prioritize rendering so that maps with higher detail are rendered on top of maps of lower detail and maps at the same detail are rendered in order from oldest updated to newest updated.

[Example 1 - Byblos](https://minecraft.greener.ca/byblos/map/overworld/)

[Example 2 - various YouTuber server maps](http://jason.green.io/static)

![screen shot 2018-02-24 at 2 04 28 pm](https://user-images.githubusercontent.com/2853489/36633991-d83f2a9a-196b-11e8-94c7-44c57c4fb40e.png)

![screen shot 2018-02-24 at 2 10 37 pm](https://user-images.githubusercontent.com/2853489/36634033-8f94dfaa-196c-11e8-88bd-fef75e7e0132.png)

## prerequisites

python3 and pip (pip3) (Not tested in python2)

You'll need to install http://jcupitt.github.io/libvips/

to do this on Mac OS X:

    brew install vips

Ubuntu should be:

    apt-get install libvips glib2.0-dev

some python stuff you'll need:

    pip3 install nbt Pillow requests pyvips

and you'll need *minecraftmap*; I've put in a pull request for the official one to fix maps in 1.12, I'm hoping to just pull this from pypi eventaully, but for now use this fork:

    git clone https://github.com/jason-green-io/minecraftmap

then, inside the new *minecraftmap* folder

    python setup.py build
    python setup.py install

## usage

```
usage: papyri.py [-h] [--poi] --mcdata MCDATA --output OUTPUT
                 [--zoomlevel ZOOMLEVEL] [--overlay] [--nostitch] [--mapstats]

convert minecraft maps to the web

optional arguments:
  -h, --help            show this help message and exit
  --poi                 generate POI file, this outputs papyri.md that can be
                        used with http://dynalon.github.io/mdwiki/#!index.md
                        to show on the web
  --mcdata MCDATA       input path to minecraft server data
  --output OUTPUT       output path for web stuff
  --zoomlevel ZOOMLEVEL
                        size of maps generated in mc zoom levels, 8 = 65k, 7 =
                        32k
  --overlay             add overlay showing map IDs
  --nostitch            disable generating the map, useful if you only want
                        the overlay displayed
  --mapstats            generate stats on map coverage of selected size
```

Once it's done, the contents of the output folder can be served as a website. It's completely static so it can but put in an S3 bucket a github project or hosted locally on your machine by running something like `python3 -m SimpleHTTPServer` inside the output folder.

## POI instructions

Step 1: Rename a book to `papyri`

![anvil](https://user-images.githubusercontent.com/2853489/36634498-7aebf294-1973-11e8-9fdb-088a5cff52c1.png)

Step 2: Follow this template, one POI per page is recommended

![book page](https://user-images.githubusercontent.com/2853489/36634615-228a5364-1975-11e8-9566-72969bb1026e.png)



## Credits

POI web front end by: http://dynalon.github.io/mdwiki/#!index.md
(this can actually be used as full fledged wiki with markdown files, pretty cool)

Font provided by: http://www.04.jp.org

DZI viewer provided by: https://openseadragon.github.io

minecraftmap map item framework by: https://github.com/spookymushroom/minecraftmap

This project is licensed under the terms of the MIT license.
