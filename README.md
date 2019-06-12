# FilebotTool: FileBot Integration for Deluge
*requires [Filebot](http://www.filebot.net/)*

**Version 1.2.6**


***NOTE: THIS PLUGIN IS NOT YET COMPATABLE WITH DELUGE 2.0***


##### [Download Latest Release](https://github.com/Laharah/deluge-FilebotTool/releases/latest)

##### [How to Install in Deluge](https://github.com/Laharah/deluge-FileBotTool/wiki)


Rename your torrents using FileBot from within deluge. Keep your media organized and
your torrents seeding **without wasting storage space on duplicates!**

![rename_dialog](http://i.imgur.com/pfc14Rs.png)

### Features:
- easy to use GUI
- cross-platform
- Automatic file re-direction
- Save frequently used profiles
- Batch processing
- Dry run previews
- Download missing subtitles
- Multi-language support
- Easily rollback mistakes
- supports both server-client and classic mode
- Custom auto-organize rulesets
- supports creating reflinks on btrfs filesystems


![prefs_page](http://i.imgur.com/Dr22k0a.png)

### How to Use:
1. Download, then install the appropriate .egg files using the plugin manager in deluge->settings
 (install both if you're not sure which to use)

2. click the checkbox next to FileBotTool to enable the plugin

2. Once Installed simply right click any torrent you'd like to sort, and select FileBotTool:

    ![right-click-menu](http://i.imgur.com/mVfmfnr.png)

3. Fill out which database you'd like to use along with the format expression and any other settings
you'd like filebot to use (click the format expression link for help).

4. press the "Dry Run" button to test your settings and see a preview of the output.

5. Optionally name your settings profile and save it for quick use later.

6. Press "Execute Filebot" to rename and sort your torrents, the window will close when the
 sorting is finished!

See the [wiki](https://github.com/Laharah/deluge-FileBotTool/wiki) for more detailed information.

### How to build:
if you want the very latest release, you can build the plugin from source.

You will need:
- git
- a version of python that matches your deluge version (2.7 by default)

##### Instructions:
- in a command window, type
```
    git clone https://github.com/Laharah/deluge-FileBotTool.git
    cd deluge-FileBotTool
    git checkout develop
```

- then to build the plugin, on linux/osx type:
```
    python2.7 setup.py bdist_egg  # replace with 2.6 if your deluge uses python 2.6
```
   or on windows:
```
    py -2.7 setup.py bdist_egg
```
- The new .egg file located in the `dist/` folder is now ready to be added to deluge.
