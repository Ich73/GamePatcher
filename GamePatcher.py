""" Author: Dominik Beese
>>> Game Patcher
<<<
"""

import argparse
import sys
import re
from os import system, listdir, makedirs, rename, remove
from os.path import join, abspath, basename, splitext, isfile, isdir, getsize
from shutil import copyfile, copytree, rmtree
from io import BytesIO
from zipfile import ZipFile
import json
from subprocess import run, DEVNULL, PIPE
from urllib.request import urlopen
import webbrowser

VERSION = 'v1.0.0'
REPOSITORY = r'Ich73/GamePatcher'


###########
## Setup ##
###########

# set windows taskbar icon
try:
	from ctypes import windll
	appid = 'gamepatcher.' + VERSION
	windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
except: pass


#############
## Updates ##
#############

def checkUpdates():
	def printCategory(text):
		print(' '*m + '~ ' + text + ' ~')
		print()
	
	def printOption(cmd, text):
		print(' '*m + '*', cmd, ':', text)
	
	try:
		# query api
		latest = r'https://api.github.com/repos/%s/releases/latest' % REPOSITORY
		with urlopen(latest, timeout = 1) as url:
			data = json.loads(url.read().decode())
		tag = data['tag_name']
		link = data['html_url']
		
		# compare versions
		def ver2int(s):
			if s[0] == 'v': s = s[1:]
			v = s.split('.')
			return sum([int(k) * 100**(len(v)-i) for i, k in enumerate(v)])
		current_version = ver2int(VERSION)
		tag_version     = ver2int(tag)
		if current_version >= tag_version: return
		
		# show message
		printTitleBox()
		print(' '*m + 'A new version of Game Patcher is available.')
		print()
		print(' '*m + 'Current Version: %s' % VERSION)
		print(' '*m + 'New Version:     %s' % tag)
		print()
		printCategory('Options')
		printOption('D', 'Download the latest release')
		printOption('C', 'Continue with the current version')
		print()
		print('-'*(w+m+4+m))
		print()
		
		# parse command
		print('Enter command:')
		command = input('>> ').strip()
		script = command.upper() if command else ''
		
		if script == 'D':
			webbrowser.open(link)
			return True
		elif script == 'C': pass
	except Exception: pass


##########
## Main ##
##########

m = 1 # left margin
w = 64 # width of title box

def printTitleBox():
	system('cls')
	def title(msg=''): print(' '*m + '║ ' + ' '*int((w-len(msg))/2) + msg + ' '*(w-len(msg)-int((w-len(msg))/2)) + ' ║')
	print()
	print(' '*m + '╔' + '═'*(w+2) + '╗')
	title('Game Patcher ' + VERSION)
	title('(https://github.com/%s)' % REPOSITORY)
	print(' '*m + '╚' + '═'*(w+2) + '╝')
	print()

def version2int(s):
	s = s[1:] # remove v
	v = [int(x) for x in s.split('.')] # split into parts
	v += [0]*(3-len(v)) # add missing parts
	return v[0]*2**10 + v[1]*2**4 + v[2] # convert to number

def int2version(v):
	return 'v%d.%d.%d' % (v // 2**10, v % 2**10 // 2**4, v % 2**10 % 2**4)

def createName(cia, patch):
	return '%s (%s).cia' % (splitext(cia)[0], splitext(patch)[0])

def escapeName(name):
	""" Espaces a filename by replacing several characters with underscores. """
	return re.sub(r'[^\w]+', '_', splitext(name)[0]).strip('_')

def automaticMappings():
	""" Tries to automatically map which patches should be applied to which cia files.
		Returns the mappings if successful, returns None otherwise.
	"""
	# collect all zip and cia files
	patches = [f for f in listdir('.') if isfile(f) and splitext(f)[1] == '.zip']
	cias = [f for f in listdir('.') if isfile(f) and splitext(f)[1].lower() == '.cia']
	
	# remove cias that look like already patched cias
	cias = [cia for cia in cias if all('(%s)' % splitext(patch)[0] not in cia for patch in patches)]
	
	# guess the versions of all patches and cias
	def guessVersions(files): return {file: (re.search(r'v\d\.\d(\.\d)?', file) or [None])[0] for file in files}
	patches = guessVersions(patches)
	cias = guessVersions(cias)
	
	# set None to v1.0 if only one version not specified
	def guessFirstVersion(files):
		if sum(1 for version in files.values() if version is None) == 1:
			return {file: version if version is not None else 'v1.0' for file, version in files.items()}
		return files
	patches = guessFirstVersion(patches)
	cias = guessFirstVersion(cias)
	
	# set cia version by file size
	if any(version is None for version in cias.values()) and len(cias) == 2 and sum(1 for version in set(patches.values()) if version not in [None, 'v1.0']) <= 1:
		update_version = next((version for version in set(patches.values()) if version not in [None, 'v1.0']), None)
		cias = sorted(cias.keys(), key=getsize, reverse=True)
		if update_version is not None: # update patch found, set version by file size
			cias = {cias[0]: 'v1.0', cias[1]: update_version}
		else: # no update patch found, only keep larger file
			cias = {cias[0]: 'v1.0'}
	
	# no duplicates cias found and at least one matching patch
	if len(set(cias.values())) == len(cias.values()) and any(version in cias.values() for version in patches.values()):
		mappings = set()
		for patch, version in patches.items():
			cia = next((cia for cia, version2 in cias.items() if version2 == version), None)
			if cia is None: continue
			ver = 0 if version is None else version2int(version)
			if version != 'v1.0': ver += 2**4 # increase version of updates by 0.1 to avoid update warnings
			mappings.add((patch, cia, ver))
		return mappings
	
	# automatic mapping not possible
	return None

def askMappings():
	""" Lets the user enter the patch files, cia files and versions manually. """
	
	def collectFiles(type, exclude = set()):
		return [f for f in listdir('.') if isfile(f) and splitext(f)[1].lower() == type and f not in exclude]
	
	def askFile(type, exclude = set()):
		files = collectFiles(type, exclude)
		for i, file in enumerate(files): print('  ', '[%d] %s' % (i+1, file))
		while True:
			idx = input('Your selection? ').strip()
			if idx.isdigit() and int(idx) in range(1, len(files)+1):
				return files[int(idx)-1]
				break
			print('Invalid selection.')
	
	if not collectFiles('.zip'):
		print('Error:', 'No patches were found.')
		print('Place the patches as a .zip file in this directory and try again.')
		print()
		input('Press Enter to exit...')
		sys.exit(2)
	if not collectFiles('.cia'):
		print('Error:', 'No cia files were found.')
		print('Place the game as a .cia file in this directory and try again.')
		print()
		input('Press Enter to exit...')
		sys.exit(2)
	
	mappings = set()
	while True:
		# ask patch
		print('Enter the Patch you want to apply:')
		patch = askFile('.zip', {p for p, _, _ in mappings})
		print()
		
		# ask cia
		print('Enter the CIA you want to apply the patch to:')
		cia = askFile('.cia')
		print()
		
		# ask version
		print('Enter the version of the patched CIA:')
		print('  ', 'It is recommended to increase the version of update CIAs by 0.1.')
		print('  ', 'If you don\'t know the version, enter 0.')
		print('  ', 'Examples: v1.0, v1.2.0.')
		while True:
			v = input('Your selection? ').strip()
			if re.match('^v\d\.\d(\.\d)?$', v) or v.isdigit():
				version = int(v) if v.isdigit() else version2int(v)
				break
			print('Invalid version.')
		print()
		
		# add to mappings
		mappings.add((patch, cia, version))
		
		# exit if no patches left
		if not collectFiles('.zip', {p for p, _, _ in mappings}): break
		
		# ask next
		command = input('Do you wish to apply another patch? [y/n] ').strip()
		print()
		if command != 'y': break
	print()
	
	# return all mappings
	return mappings

def downloadExe(download_url, filename):
	""" Downloads an exe file form the given [download_url], puts it in the current directory
		and renames it to [filename].
		If the download is a zip file it uses the first exe file found in the archive.
	"""
	# check if already exists
	if isfile(filename):
		print('Found', filename)
		return
	
	# get type and download data
	print('Downloading', basename(download_url))
	print(' ', 'from', download_url)
	type = splitext(download_url)[1]
	with urlopen(download_url) as url: data = url.read()
	
	# zip file
	if type == '.zip':
		with ZipFile(BytesIO(data)) as zip:
			file = next((file for file in zip.infolist() if splitext(file.filename)[1] == '.exe'), None)
			if not file: raise Exception('The downloaded zip file does not contain an exe file.')
			print('Extracting', basename(file.filename))
			zip.extract(file)
			rename(basename(file.filename), filename)
	
	# exe
	elif type == '.exe':
		with open(filename, 'wb') as file:
			file.write(data)
	
	# not supported
	else: raise Exception('The download link does not point towards a zip or exe file.')
	
	# success
	print('Downloaded', filename)
	print()

def extractCIA(cia_file):
	""" Extracts the given [cia_file]. """
	try:
		# check if already exists
		cia_dir = escapeName(cia_file)
		if isdir(cia_dir):
			print('Found', cia_dir)
			return True
		print('Extract', cia_file)
		
		# step 1: CIA -> DecryptedPartitionX.bin
		print('Extracting Step 1/3')
		makedirs(cia_dir, exist_ok=True)
		proc = run('ctrtool -x --content="%s" "%s"' % (abspath(join(cia_dir, 'Decrypted')), cia_file), stdout=DEVNULL, stderr=PIPE)
		if proc.returncode != 0: raise Exception(proc.stderr.decode())
		partitions = list()
		for decrypted_file in listdir(cia_dir):
			id = int(decrypted_file[10:14])
			rename(join(cia_dir, decrypted_file), join(cia_dir, 'DecryptedPartition%d.bin' % id))
			partitions.append(id)
		
		# step 2: DecryptedPartitionX.bin -> HeaderNCCHX.bin, DecryptedXXX.bin, ...
		print('Extracting Step 2/3')
		copyfile('3dstool.exe', join(cia_dir, '3dstool.exe'))
		if 0 in partitions:
			print(' ', 'Partition0')
			proc = run('3dstool -xtf cxi DecryptedPartition0.bin --header HeaderNCCH0.bin --exh DecryptedExHeader.bin --exefs DecryptedExeFS.bin --romfs DecryptedRomFS.bin --logo LogoLZ.bin --plain PlainRGN.bin', cwd=cia_dir, stdout=DEVNULL, stderr=PIPE)
			if proc.returncode != 0: raise Exception(proc.stderr.decode())
		if 1 in partitions:
			print(' ', 'Partition1')
			proc = run('3dstool -xtf cfa DecryptedPartition1.bin --header HeaderNCCH1.bin --romfs DecryptedManual.bin', cwd=cia_dir, stdout=DEVNULL, stderr=PIPE)
			if proc.returncode != 0: raise Exception(proc.stderr.decode())
		if 2 in partitions:
			print(' ', 'Partition2')
			proc = run('3dstool -xtf cfa DecryptedPartition2.bin --header HeaderNCCH2.bin --romfs DecryptedDownloadPlay.bin', cwd=cia_dir, stdout=DEVNULL, stderr=PIPE)
			if proc.returncode != 0: raise Exception(proc.stderr.decode())
		for id in partitions: remove(join(cia_dir, 'DecryptedPartition%d.bin' % id))
		
		# step 3: DecryptedExeFS.bin -> ExtractedExeFS
		print('Extracting Step 3/3')
		if 0 in partitions:
			proc = run('3dstool -xtf exefs DecryptedExeFS.bin --exefs-dir ExtractedExeFS --header HeaderExeFS.bin', cwd=cia_dir, stdout=DEVNULL, stderr=PIPE)
			if proc.returncode != 0: raise Exception(proc.stderr.decode())
			exefs_dir = join(cia_dir, 'ExtractedExeFS')
			if isfile(join(exefs_dir, 'banner.bnr')): rename(join(exefs_dir, 'banner.bnr'), join(exefs_dir, 'banner.bin'))
			if isfile(join(exefs_dir, 'icon.icn')):   rename(join(exefs_dir, 'icon.icn'),   join(exefs_dir, 'icon.bin'))
		remove(join(cia_dir, '3dstool.exe'))
		
		# success
		print('Extracted to', cia_dir)
		print()
		return True
		
	except Exception as e:
		print(str(e).strip())
		print('ERROR: Extracting Failed')
		print()
		return False

def prepareCIA(patch_file, cia_file):
	""" Copies all files from the original cia to the patch cia folder.
		Creates CustomXXX files for all XXX files.
	"""
	# check if already exists
	orig_dir = escapeName(cia_file)
	cia_dir = escapeName(createName(cia_file, patch_file))
	if isdir(cia_dir):
		print('Found', cia_dir)
		return True
	print('Copy', orig_dir)
	
	# copy folder
	copytree(orig_dir, cia_dir)
	
	# copy files
	def ct(x, y):
		if isdir(join(cia_dir, x)): copytree(join(cia_dir, x), join(cia_dir, y))
	def cf(x, y):
		if isfile(join(cia_dir, x)): copyfile(join(cia_dir, x), join(cia_dir, y))
	ct('ExtractedExeFS', 'CustomExeFS')
	cf('HeaderExeFS.bin', 'CustomHeaderExeFS.bin')
	cf('DecryptedExeFS.bin', 'CustomExeFS.bin')
	cf('DecryptedExHeader.bin', 'CustomExHeader.bin')
	cf('DecryptedRomFS.bin', 'CustomRomFS.bin')
	cf('HeaderNCCH0.bin', 'CustomHeaderNCCH0.bin')
	cf('LogoLZ.bin', 'CustomLogoLZ.bin')
	cf('PlainRGN.bin', 'CustomPlainRGN.bin')
	cf('DecryptedManual.bin', 'CustomManual.bin')
	cf('HeaderNCCH1.bin', 'CustomHeaderNCCH1.bin')
	cf('DecryptedDownloadPlay.bin', 'CustomDownloadPlay.bin')
	cf('HeaderNCCH2.bin', 'CustomHeaderNCCH2.bin')
	
	# success
	print('Copied to', cia_dir)
	print()
	return True

def rebuildCIA(patch_file, cia_file, version = 1024):
	""" Rebuilds the cia file defined by the given [cia_file] and [patch_file]. """
	try:
		# check if exists
		rebuilt_cia_file = createName(cia_file, patch_file)
		cia_dir = escapeName(rebuilt_cia_file)
		if isfile(rebuilt_cia_file): remove(rebuilt_cia_file)
		print('Rebuild', cia_dir)
		
		# step 1: CustomExeFS -> CustomExeFS.bin
		print('Rebuilding Step 1/3')
		copyfile('3dstool.exe', join(cia_dir, '3dstool.exe'))
		exefs_dir = join(cia_dir, 'CustomExeFS')
		if isdir(exefs_dir) and isfile(join(cia_dir, 'CustomHeaderExeFS.bin')):
			if isfile(join(exefs_dir, 'banner.bin')): rename(join(exefs_dir, 'banner.bin'), join(exefs_dir, 'banner.bnr'))
			if isfile(join(exefs_dir, 'icon.bin')):   rename(join(exefs_dir, 'icon.bin'),   join(exefs_dir, 'icon.icn'))
			proc = run('3dstool -ctf exefs CustomExeFS.bin --exefs-dir CustomExeFS --header CustomHeaderExeFS.bin', cwd=cia_dir, stdout=DEVNULL, stderr=PIPE)
			if proc.returncode != 0: raise Exception(proc.stderr.decode())
			if isfile(join(exefs_dir, 'banner.bnr')): rename(join(exefs_dir, 'banner.bnr'), join(exefs_dir, 'banner.bin'))
			if isfile(join(exefs_dir, 'icon.icn')):   rename(join(exefs_dir, 'icon.icn'),   join(exefs_dir, 'icon.bin'))
		
		# step 2: CustomHeaderNCCHX.bin, CustomDecryptedXXX.bin, ... -> DecryptedPartitionX.bin
		print('Rebuilding Step 2/3')
		if all(isfile(join(cia_dir, f)) for f in ['CustomHeaderNCCH0.bin', 'CustomExHeader.bin', 'CustomExeFS.bin', 'CustomRomFS.bin', 'CustomLogoLZ.bin', 'CustomPlainRGN.bin']):
			print(' ', 'Partition0')
			proc = run('3dstool -ctf cxi CustomPartition0.bin --header CustomHeaderNCCH0.bin --exh CustomExHeader.bin --exefs CustomExeFS.bin --romfs CustomRomFS.bin --logo CustomLogoLZ.bin --plain CustomPlainRGN.bin', cwd=cia_dir, stdout=DEVNULL, stderr=PIPE)
			if proc.returncode != 0: raise Exception(proc.stderr.decode())
		if all(isfile(join(cia_dir, f)) for f in ['CustomHeaderNCCH1.bin', 'CustomManual.bin']):
			print(' ', 'Partition1')
			proc = run('3dstool -ctf cfa CustomPartition1.bin --header CustomHeaderNCCH1.bin --romfs CustomManual.bin', cwd=cia_dir, stdout=DEVNULL, stderr=PIPE)
			if proc.returncode != 0: raise Exception(proc.stderr.decode())
		if all(isfile(join(cia_dir, f)) for f in ['CustomHeaderNCCH2.bin', 'CustomDownloadPlay.bin']):
			print(' ', 'Partition2')
			proc = run('3dstool -ctf cfa CustomPartition2.bin --header CustomHeaderNCCH2.bin --romfs CustomDownloadPlay.bin', cwd=cia_dir, stdout=DEVNULL, stderr=PIPE)
			if proc.returncode != 0: raise Exception(proc.stderr.decode())
		remove(join(cia_dir, '3dstool.exe'))
		
		# step 3: DecryptedPartitionX.bin -> CIA
		print('Rebuilding Step 3/3')
		print(' ', 'CIA', int2version(version))
		contents = ['-content "%s":%s:%s' % (join(cia_dir, f), f[15], f[15]) for f in listdir(cia_dir) if f.startswith('CustomPartition')]
		proc = run('makerom -f cia %s -ver %d -o "%s" -target p -ignoresign' % (' '.join(contents), version, rebuilt_cia_file), stdout=DEVNULL, stderr=PIPE)
		if proc.returncode != 0: raise Exception(proc.stderr.decode())
		for file in [f for f in listdir(cia_dir) if f.startswith('CustomPartition')]: remove(join(cia_dir, file))
		
		# success
		print('Rebuilt', rebuilt_cia_file)
		print()
		return True
		
	except Exception as e:
		print(str(e).strip())
		print('ERROR: Rebuild Failed')
		print()
		return False

def applyPatches(patch_file, cia_file, patches, ignore_incompatible_patches = False):
	""" Extracts the patches in [patch_file] and applies them to the extracted [cia_file].
		Applies the patches to the files as defined in [patches].
	"""
	try:
		cia_dir = escapeName(createName(cia_file, patch_file))
		print('Apply', patch_file, '→', cia_file)
		
		# extract patches
		print('Extract', patch_file)
		patch_dir = join(cia_dir, 'Patches')
		with ZipFile(patch_file, 'r') as file:
			file.extractall(patch_dir)
		
		# apply patches
		copyfile('xdelta.exe', join(cia_dir, 'xdelta.exe'))
		for patch in listdir(patch_dir):
			if patch not in patches: raise Exception('Unknown patch', patch)
			print('Apply', patch)
			orig, custom = patches[patch]
			proc = run('xdelta -f -d -s %s Patches/%s %s' % (orig, patch, custom), cwd=cia_dir, stdout=DEVNULL, stderr=PIPE)
			if proc.returncode != 0:
				if ignore_incompatible_patches:
					print(proc.stderr.decode().strip())
					print('WARNING: Failed to apply', patch)
				else: raise Exception(proc.stderr.decode())
		
		# clean up
		remove(join(cia_dir, 'xdelta.exe'))
		rmtree(patch_dir)
		print('Applied', patch_file)
		print()
		return True
		
	except Exception as e:
		print(str(e).strip())
		print('ERROR: Patching Failed')
		print()
		return False

def cleanUp(mappings = None, files = None):
	""" Deletes all directories used by the given [mappings] and all given [files].
		If [mappings] is None all directories will be deleted.
	"""
	def rmdir(dir):
		if not isdir(dir): return
		print('Delete', dir)
		rmtree(dir)
	def rmfile(file):
		if not isfile(file): return
		print('Delete', file)
		remove(file)
	if mappings is not None: # delete mappings
		for patch_file, cia_file, _ in mappings:
			rmdir(escapeName(cia_file))
			rmdir(escapeName(createName(cia_file, patch_file)))
	else: # delete all
		for dir in [f for f in listdir('.') if isdir(f)]:
			rmdir(dir)
	if files:
		for file in files:
			rmfile(file)

class ValidateMapping(argparse.Action):
	""" Validates a mapping.
		Checks that the first and second arguments are a valid file.
		Checks that the third argument is a version string or version number.
	"""
	def __call__(self, parser, args, values, option_string=None):
		# unpack values
		patch, cia, version = values
		# check values
		if not isfile(patch): raise FileNotFoundError('No such file: \'%s\'' % patch)
		if not isfile(cia):   raise FileNotFoundError('No such file: \'%s\'' % cia)
		if not re.match('^v\d\.\d(\.\d)?$', version) and not version.isdigit():
			raise ValueError('Not a valid version: \'%s\'' % version)
		# convert version to int
		ver = int(version) if version.isdigit() else version2int(version)
		# add current mapping to list of mappings
		if not hasattr(self, 'mappings'): self.mappings = list()
		self.mappings.append((patch, cia, ver))
		# set attribute
		setattr(args, self.dest, self.mappings)

def main():
	try:
		# check updates
		if len(sys.argv) <= 1:
			if checkUpdates(): return
		
		# argparse
		parser = argparse.ArgumentParser()
		parser.add_argument('--mapping', metavar=('patch', 'cia', 'version'), dest='mappings', nargs=3, action=ValidateMapping, \
			help='Defines which patch file should be used to patch which cia file. Sets the version of the patched cia file as a string (e.g. v1.0.0) or integer (e.g. 1024). Can be used multiple times.')
		parser.add_argument('--ignore-incompatible-patches', dest='ignore_incompatible_patches', action='store_const', \
			const=True, default=False, \
			help='Continue patching when a patch cannot be applied instead of stopping the process.')
		parser.add_argument('--xdelta-url', metavar='url', dest='xdelta_url', nargs=1, \
			default=[r'https://github.com/jmacd/xdelta-gpl/releases/download/v3.1.0/xdelta3-3.1.0-x86_64.exe.zip'], \
			help='The direct download link to xdelta. Supported file types are zip and exe.')
		parser.add_argument('--3dstool-url', metavar='url', dest='dstool_url', nargs=1, \
			default=[r'https://github.com/dnasdw/3dstool/releases/download/v1.2.6/3dstool.zip'], \
			help='The direct download link to 3dstool. Supported file types are zip and exe.')
		parser.add_argument('--ctrtool-url', metavar='url', dest='ctrtool_url', nargs=1, \
			default=[r'https://github.com/3DSGuy/Project_CTR/releases/download/ctrtool-v0.7/ctrtool-v0.7-win_x86_64.zip'], \
			help='The direct download link to ctrtool. Supported file types are zip and exe.')
		parser.add_argument('--makerom-url', metavar='url', dest='makerom_url', nargs=1, \
			default=[r'https://github.com/3DSGuy/Project_CTR/releases/download/makerom-v0.17/makerom-v0.17-win_x86_64.zip'], \
			help='The direct download link to makerom. Supported file types are zip and exe.')
		parser.add_argument('--romfs', metavar='file', dest='patch_romfs', nargs=1, default='RomFS.xdelta', \
			help='The name of the patch file for DecryptedRomFS.bin')
		parser.add_argument('--manual', metavar='file', dest='patch_manual', nargs=1, default='Manual.xdelta', \
			help='The name of the patch file for DecryptedManual.bin')
		parser.add_argument('--download-play', metavar='file', dest='patch_download_play', nargs=1, default='DownloadPlay.xdelta', \
			help='The name of the patch file for DecryptedDownloadPlay.bin')
		parser.add_argument('--banner', metavar='file', dest='patch_banner', nargs=1, default='banner.xdelta', \
			help='The name of the patch file for banner.bin')
		parser.add_argument('--code', metavar='file', dest='patch_code', nargs=1, default='code.xdelta', \
			help='The name of the patch file for code.bin')
		parser.add_argument('--icon', metavar='file', dest='patch_icon', nargs=1, default='icon.xdelta', \
			help='The name of the patch file for icon.bin')
		parser.add_argument('--logo', metavar='file', dest='patch_logo', nargs=1, default='LogoLZ.xdelta', \
			help='The name of the patch file for LogoLZ.bin')
		parser.add_argument('--plain', metavar='file', dest='patch_plain', nargs=1, default='PlainRGN.xdelta', \
			help='The name of the patch file for LogoLZ.bin')
		parser.add_argument('--ex-header', metavar='file', dest='patch_ex_header', nargs=1, default='ExHeader.xdelta', \
			help='The name of the patch file for DecryptedExHeader.bin')
		parser.add_argument('--header0', metavar='file', dest='patch_header0', nargs=1, default='HeaderNCCH0.xdelta', \
			help='The name of the patch file for HeaderNCCH0.bin')
		parser.add_argument('--header1', metavar='file', dest='patch_header1', nargs=1, default='HeaderNCCH1.xdelta', \
			help='The name of the patch file for HeaderNCCH1.bin')
		parser.add_argument('--header2', metavar='file', dest='patch_header2', nargs=1, default='HeaderNCCH2.xdelta', \
			help='The name of the patch file for HeaderNCCH2.bin')
		args = parser.parse_args()
		
		# title
		printTitleBox()
		
		# mappings
		if args.mappings is not None:
			mappings = set(args.mappings)
		else:
			mappings = automaticMappings()
			if mappings is None:
				if len(sys.argv) <= 1: mappings = askMappings()
				else: raise ValueError('The mappings could not be assigned automatically.')
		mappings = sorted(mappings)
		
		# patches
		patches = {
			args.patch_romfs:         ('DecryptedRomFS.bin', 'CustomRomFS.bin'),
			args.patch_manual:        ('DecryptedManual.bin', 'CustomManual.bin'),
			args.patch_download_play: ('DecryptedDownloadPlay.bin', 'CustomDownloadPlay.bin'),
			args.patch_banner:        (join('ExtractedExeFS', 'banner.bin'), join('CustomExeFS', 'banner.bin')),
			args.patch_code:          (join('ExtractedExeFS', 'code.bin'), join('CustomExeFS', 'code.bin')),
			args.patch_icon:          (join('ExtractedExeFS', 'icon.bin'), join('CustomExeFS', 'icon.bin')),
			args.patch_logo:          ('LogoLZ.bin', 'CustomLogoLZ.bin'),
			args.patch_plain:         ('PlainRGN.bin', 'CustomPlainRGN.bin'),
			args.patch_ex_header:     ('DecryptedExHeader.bin', 'CustomExHeader.bin'),
			args.patch_header0:       ('HeaderNCCH0.bin', 'CustomHeaderNCCH0.bin'),
			args.patch_header1:       ('HeaderNCCH1.bin', 'CustomHeaderNCCH1.bin'),
			args.patch_header2:       ('HeaderNCCH2.bin', 'CustomHeaderNCCH2.bin')
		}
		
		# main
		print('~~ Download Tools ~~')
		downloadExe(args.xdelta_url[0],  'xdelta.exe')
		downloadExe(args.dstool_url[0],  '3dstool.exe')
		downloadExe(args.ctrtool_url[0], 'ctrtool.exe')
		downloadExe(args.makerom_url[0], 'makerom.exe')
		print()
		
		print('~~ Extract CIAs ~~')
		fails = list()
		for cia_file in {cia for _, cia, _ in mappings}:
			success = extractCIA(cia_file)
			if not success: fails.append(cia_file)
		print()
		
		print('~~ Patch CIAs ~~')
		for patch_file, cia_file, _ in mappings:
			if cia_file in fails:
				print('Skip', patch_file, '→', cia_file)
				fails.append((patch_file, cia_file))
				continue
			prepareCIA(patch_file, cia_file)
			success = applyPatches(patch_file, cia_file, patches, args.ignore_incompatible_patches)
			if not success: fails.append((patch_file, cia_file))
		print()
		
		print('~~ Rebuild CIAs ~~')
		for patch_file, cia_file, version in mappings:
			if (patch_file, cia_file) in fails:
				print('Skip', patch_file, '→', cia_file)
				continue
			success = rebuildCIA(patch_file, cia_file, version)
			if not success: fails.append((patch_file, cia_file))
		print()
		
		print('~~ Summary ~~')
		for patch_file, cia_file, _ in mappings:
			if (patch_file, cia_file) in fails: print('Failed', patch_file, '→', cia_file)
			else: print('Created', createName(cia_file, patch_file))
		
	except Exception as e:
		import traceback
		traceback.print_exc()
	
	print()
	command = input('Finished. Clean up? [y/n/all] ').strip()
	if command in ['y', 'all']:
		print()
		print('~~ Clean Up ~~')
		if command == 'y': cleanUp(mappings=mappings)
		else: cleanUp(mappings=None, files=['xdelta.exe', '3dstool.exe', 'ctrtool.exe', 'makerom.exe'])
		print()
		input('Press Enter to exit...')

if __name__ == '__main__':
	main()
