#!/usr/bin/python3
from gpapi.googleplay import GooglePlayAPI
import os
import sys
import argparse
import json
import pickle
from os.path import expanduser
import validators
from termcolor import colored
from getpass import getpass

devicecode = 'bacon'

ap = argparse.ArgumentParser(description='Command line APK downloader for Google Play Store.')
ap.add_argument('-c', '--configure', dest='configure', action='store_const', const=True, help='Create the configuration file by providing your Google email and password (preferably app password).', default=False)
ap.add_argument('-id', '--packageId', dest='packageId', help='Package ID of the app, i.e. com.whatsapp')
ap.add_argument('-e', '--email', dest='email', help='Google username', default=None)
ap.add_argument('-p', '--password', dest='password', help='Google password', default=None)
ap.add_argument('-d', '--directory', dest='storagepath', help='Path where to store downloaded files', default=False)
ap.add_argument('-dc', '--deviceCode', dest='deviceCode', help='Device code name', default=devicecode)
ap.add_argument('-ex', '--expansionfiles', dest='expansionfiles', action='store_const', const=True, help='Download expansion (OBB) data if available', default=True)

args = ap.parse_args()

HOMEDIR = expanduser("~/.gplaydl/")
CACHEDIR = HOMEDIR+'cache/';
CACHEFILE = CACHEDIR + args.deviceCode + '.txt'
CONFIGDIR = HOMEDIR+'config/';
CONFIGFILE = CONFIGDIR + 'config.txt'


def sizeof_fmt(num):
    for unit in ['', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB']:
        if abs(num) < 1024.0:
            return "%3.1f%s" % (num, unit)
        num /= 1024.0
    return "%.1f%s" % (num, 'Yi')

def configureauth(email=None, password=None):
	while email is None:
		em = input("Google Email: ").strip()
		if validators.email(em):
			email = em
		else:
			print(colored('Provided email is invalid.', 'red'))

	while password is None:
		password = getpass("Google Password: ").strip()
		if len(password) == 0:
			password = None

	if not os.path.exists(CONFIGDIR):
		os.makedirs(os.path.dirname(CONFIGDIR))

	server = GooglePlayAPI('en_US', 'America/New York', devicecode)
	try:
		server.login(email, password)
		server.details('com.whatsapp')
		config = {'email': email, 'password': password}
		pickle.dump(config, open(CONFIGFILE, "wb"))
		print(colored('Configuration file created successfully! Try downloading an APK file now.', 'green'))
	except:
		print(colored('Provided login credentials seem to be invalid.', 'yellow'))
		configureauth()


def downloadapp(packageId, email=None, password=None, expansionFiles=True, storagepath='./'):
	if email is None and password is None:
		if os.path.exists(CONFIGFILE):
			with open(CONFIGFILE, "rb") as f:
				config = pickle.load(f)
				email = config['email']
				password = config['password']
		else:
			configureauth()

		server = GooglePlayAPI('en_US', 'America/New York', args.deviceCode)
		try:
			server = do_login(server, email, password)
		except Exception as e:
			print(colored('Login failed. Please re-configure your auth.', 'yellow'))
			configureauth()
		
		try:
			print(colored('Attempting to download ' + packageId, 'blue'))
			download = server.download(packageId, expansion_files=expansionFiles)
			apkfname = download['docId'] + '.apk'
			apkpath = os.path.join(storagepath, apkfname)
			if not os.path.isdir(storagepath):
				os.makedirs(storagepath)
			saved = 0
			totalsize = int(download.get('file').get('total_size'))
			print(colored('Downloading ' + apkfname + '.....', 'blue'))
			with open(apkpath, 'wb') as first:
				for chunk in download.get('file').get('data'):
					saved += len(chunk)
					first.write(chunk)
					done = int(50 * saved / totalsize)
					sys.stdout.write("\r[%s%s] %s%s (%s/%s)" % ('*' * done, ' ' * (50-done), int((saved/totalsize)*100), '%', sizeof_fmt(saved), sizeof_fmt(totalsize)))
			print('')
			print(colored('APK downloaded and stored at ' + apkpath, 'green'))

			for obb in download['additionalData']:
				name = obb['type'] + '.' + str(obb['versionCode']) + '.' + download['docId'] + '.obb'
				print(colored('Downloading ' + name + '.....', 'blue'))
				obbpath = os.path.join(storagepath, download['docId'], name)
				if not os.path.isdir(os.path.join(storagepath, download['docId'])):
					os.makedirs(os.path.join(storagepath, download['docId']))
				
				saved = 0
				totalsize = int(obb.get('file').get('total_size'))
				with open(obbpath, 'wb') as second:
					for chunk in obb.get('file').get('data'):
						second.write(chunk)
						saved += len(chunk)
						done = int(50 * saved / totalsize)
						sys.stdout.write("\r[%s%s] %s%s (%s/%s)" % ('*' * done, ' ' * (50-done), int((saved/totalsize)*100), '%', sizeof_fmt(saved), sizeof_fmt(totalsize)))
				print('')
				print(colored('OBB file downloaded and stored at ' + obbpath, 'green'))
		except Exception as e:
			print(str(e))
			print(colored('Download failed. gplaydl cannot download some apps that are paid or incompatible.', 'red'))

def write_cache(gsfId, token):
	if not os.path.exists(CACHEDIR):
		os.makedirs(os.path.dirname(CACHEDIR))
	info = {'gsfId': gsfId, 'token': token}
	pickle.dump(info, open(CACHEFILE, "wb"))

def read_cache():
	try:
		with open(CACHEFILE, "rb") as f:
			info = pickle.load(f)
	except:
		info = None
	return info

def refresh_cache(server, email, password):
	server.login(email, password, None, None)
	write_cache(server.gsfId, server.authSubToken)
	return server

def do_login(server, email, password):
	cacheinfo = read_cache()
	if cacheinfo:
		# Sign in using cached info
		try:
			server.login(None, None, cacheinfo['gsfId'], cacheinfo['token'])
		except:
			refresh_cache(email, password)
	else:
		# Re-authenticate using email and pass and save info to cache
		refresh_cache(server, email, password)
	return server

def main():
	if args.email:
		email = args.email
	else:
		email = None

	if args.password:
		password = args.password
	else:
		password = None

	if args.storagepath:
		storagepath = args.storagepath
	else:
		storagepath = './'

	if args.configure:
		configureauth(email, password)
		sys.exit(0)

	if args.packageId:
		downloadapp(packageId=args.packageId, email=email, password=password,
		            expansionFiles=args.expansionfiles, storagepath=storagepath)
		sys.exit(0)

	if not args.packageId or not args.configure:	
		ap.print_help()
