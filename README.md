#FilebotTool:FileBot integration for Deluge
*requires [Filebot](http://www.filebot.net/)*

**Version Beta 0.7.3**

*Download [HERE](https://github.com/Laharah/deluge-FilebotTool/releases/latest)*


Rename your torrents using FileBot from within deluge. Keep your media organized and 
your torrents seeding **without wasting storage space on duplicates!**

![rename_dialog](http://i.imgur.com/pfc14Rs.png)

###Features:
- easy to use GUI
- cross-platform
- Automatic file re-direction
- Save frequently used profiles
- Batch processing
- Dry run previews
- Download missing subtitles *(temporarily disabled)*
- Easily rollback mistakes
- supports both server-client and classic mode
- Custom auto-organize rulesets:


![prefs_page](http://i.imgur.com/Dr22k0a.png)

####How to build:
if you want the very latest release, you can build the plugin from source.

You will need:
- git
- a version of python that matches your deluge version (2.6 by default)

######Instructions:
- in a command window, type
```
    git clone https://github.com/Laharah/deluge-FileBotTool.git
    cd deluge-FileBotTool
    git checkout develop
```

- then to build the plugin, on linux/osx type:
```
    python2.6 setup.py bdist_egg  # replace with 2.7 if deluge uses python 2.7
``` 
   or on windows:
```
    py -2.6 setup.py bdist_egg
``` 
- The new .egg file located in the `dist/` folder is now ready to be added to deluge. 

####Planned Release Features:
- individual file filtering and rule matching
- better logging
- more UI polish