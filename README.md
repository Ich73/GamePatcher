# Game Patcher
Game Patcher is a small program to simplify the workflow of patching CIA and 3DS files.  
  
It uses the following tools:
  * [xdelta](https://github.com/jmacd/xdelta-gpl) ([v3.1.0](https://github.com/jmacd/xdelta-gpl/releases/tag/v3.1.0))
  * [3dstool](https://github.com/dnasdw/3dstool) ([v1.1.0](https://github.com/dnasdw/3dstool/releases/tag/v1.1.0))
  * [ctrtool](https://github.com/3DSGuy/Project_CTR) ([v0.7](https://github.com/3DSGuy/Project_CTR/releases/tag/ctrtool-v0.7))
  * [makerom](https://github.com/3DSGuy/Project_CTR) ([v0.17](https://github.com/3DSGuy/Project_CTR/releases/tag/makerom-v0.17))


## Using Game Patcher
You can download the newest version as an executable from the [Release Page](https://github.com/Ich73/GamePatcher/releases/latest). Copy `GamePatcher.exe` to the directory containing the dumped CIA or 3DS file of your game and the patches as a zip archive and run it.  
  
It supports regular CIAs, update CIAs and 3DS files and tries to automatically determine which `.zip` patches should be used to patch which `.cia` and `.3ds` games. The required tools are downloaded automatically.  
  
At the end of the script you are asked whether you want to start the clean up.
  * Choosing `n` will preserve all folders and tools and therefore speed up the next execution.
  * Choosing `y` will delete all the folders created in the current execution.
  * Choosing `all` will delete all folders in the current directory as well as all the downloaded tools.
  
You can supply the following command line arguments:
```
usage: GamePatcher [-h] [--mapping patch cia version] [--ignore-incompatible-patches] [--xdelta-url url]
                   [--3dstool-url url] [--ctrtool-url url] [--makerom-url url] [--romfs file] [--manual file]
                   [--download-play file] [--banner file] [--code file] [--icon file] [--logo file] [--plain file]
                   [--ex-header file] [--header0 file] [--header1 file] [--header2 file]

optional arguments:
  -h, --help            show this help message and exit
  --mapping patch game version
                        Defines which patch file should be used to patch which game file. Can be used multiple times.
                        When patching a CIA file specify the version as a string (v1.0.0) or integer (1024). When
                        patching a 3DS file the version will be ignored.
  --ignore-incompatible-patches
                        Continue patching when a patch cannot be applied instead of stopping the process.
  --xdelta-url url      The direct download link to xdelta. Supported file types are zip and exe.
  --3dstool-url url     The direct download link to 3dstool. Supported file types are zip and exe.
  --ctrtool-url url     The direct download link to ctrtool. Supported file types are zip and exe.
  --makerom-url url     The direct download link to makerom. Supported file types are zip and exe.
  --romfs file          The name of the patch file for DecryptedRomFS.bin
  --manual file         The name of the patch file for DecryptedManual.bin
  --download-play file  The name of the patch file for DecryptedDownloadPlay.bin
  --banner file         The name of the patch file for banner.bin
  --code file           The name of the patch file for code.bin
  --icon file           The name of the patch file for icon.bin
  --logo file           The name of the patch file for LogoLZ.bin
  --plain file          The name of the patch file for LogoLZ.bin
  --ex-header file      The name of the patch file for DecryptedExHeader.bin
  --header0 file        The name of the patch file for HeaderNCCH0.bin
  --header1 file        The name of the patch file for HeaderNCCH1.bin
  --header2 file        The name of the patch file for HeaderNCCH2.bin
```


## For Developers
### Setup
This program is written using [Python 3.8](https://www.python.org/downloads/release/python-383/).

### Running
You can run the program by using the command `python GamePatcher.py`.

### Distributing
To pack the program into a single executable file, [pyinstaller](http://www.pyinstaller.org/) is needed. Simply run the command `pyinstaller GamePatcher.spec --noconfirm` and the executable will be created in the `dist` folder.
