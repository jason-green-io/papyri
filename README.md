# papyri version 1.0.1

Papyri is a Minecraft map item web presenter. It will show all maps and banners created on a server positioned and scaled properly, creating a mosaic of your world as explored with maps. Since many maps can be created of the same area, Papyri will prioritize rendering so that maps with higher detail are rendered on top of maps of lower detail and maps at the same detail are rendered in order from oldest updated to newest updated.

[Example - Byblos](https://minecraft.greener.ca/byblos/)

![Papyri](https://user-images.githubusercontent.com/2853489/73033344-bc220880-3e0f-11ea-8715-f99dcd3494d7.png)

## prerequisites

python3 and pip (pip3) (Not tested in python2)


some python stuff you'll need:

    pip3 install tqdm nbtlib Pillow

## usage

```
usage: papyri.py [-h] --world WORLD [--includeunlimitedtracking] --output
                 OUTPUT [--copytemplate]
convert minecraft maps to the web
optional arguments:
  -h, --help            show this help message and exit
  --world WORLD         location of your world folder or save folder
  --includeunlimitedtracking
                        include maps that have unlimited tracking on, this
                        includes older maps from previous Minecraft versions
                        and treasure maps in +1.13
  --output OUTPUT       output path for web stuff
  --copytemplate        copy default index.html and assets (do this if a new
                        release changes the tempalte)
```

Once it's done, the contents of the output folder can be served as a website. It's completely static so it can be put in an S3 bucket a github project or hosted locally on your machine by running something like `python3 -m http.server` inside the output folder.


This project is licensed under the terms of the MIT license.
