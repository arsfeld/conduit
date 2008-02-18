#!/usr/bin/env python
#
# Python script useful to maintainers.
# Copyright (C) 2006-2007 Martyn Russell <martyn@imendio.com> 
#
# This script will:
#  - Summarise bugs mentioned in the ChangeLog (from Bugzilla)
#  - List translation updates
#  - List bugs fixed
#  - Output the summary and translations using a template (in HTML too)
#  - Upload your tarball and install the module.
#  - Create the email for you just to send it.
#
# Usage:
#  - You should run this script from the directory of the project you maintain.
#  - You need to specify a revision to compare the HEAD/TRUNK.
#  
# Changes:
#  - If you make _ANY_ changes, please send them in so I can incorporate them.
#
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import sys
import os
import string
import re
import urllib
import csv
import optparse
import time
import datetime 
import gnomevfs, gobject
import StringIO
from string import Template

# Script
script_name = 'Maintainer'
script_version = '0.8'
script_about = 'A script to do the laborious tasks when releasing a GNOME project.'

# Translation directories
po_dir = 'po'
help_dir = 'help'

# Commands
vc_command = ''
vc_parameters = ''

# Addresses
upload_server = 'master.gnome.org'

# Formatting 
format_bullet = '*'
format_date = '%d %B %Y'

# Cached bug IDs to names
bug_names = {}

# Cached package info
package_name = ''
package_version = ''
package_module = ''

# Default templates
template = '''
$name $version is now available for download from:
$download

$md5sums

What is it?
===========
$about

Where can I find out more?
==========================
You can visit the project web site:
$website

What's New?
===========
$news

Bugs Fixed:
===========
$fixed

Translations:
=============
$translations

Help Manual Translations:
====================
$help_translations


$footer
'''

template_in_html = '''
<p>$name $version is now available for download from:</p>
<ul>
  <li><a href="$download">$download</a></li>
</ul>
<p>$md5sums</p>

<h3>What is it?</h3>
<p>$about</p>

<h3>Where can I find out more?</h3>
<p>You can visit the project web site:</p>
<ul>
  <li><a href="$website">$website</a></li>
</ul>

<h3>What's New</h3>
$news

<h3>Bugs Fixed</h3>
$fixed

<h3>Translations</h3>
$translations

<h3>Help Manual Translations</h3>
$help_translations

$footer
'''

template_update_news = '''
NEW in $version:
==============
$news
$fixed

Translations:
$translations

Help Manual Translations:
$help_translations

'''

def get_package_info():
	global package_name
	global package_version
	global package_module
	global vc_command
	global vc_paramters

	# Don't do this ALL over again if we already have the information
	if len(package_name) > 0:
		return

	if os.path.exists('CVS'):
		if opts.debug: 
			print 'Version control system is CVS'

		vc_command = 'cvs'
		vc_parameters = '-u'
	elif os.path.exists('.svn'):
		if opts.debug: 
			print 'Version control system is SVN'

		vc_command = 'svn'
		vc_parameters = ''
	else:
		print 'Version control system unrecognised, not cvs or svn'
		sys.exit(1)
		
	if opts.package_name and opts.package_version and opts.package_module:
		if opts.debug: 
			print 'Overriding config.h check for package information'
		package_name = opts.package_name;
		package_version = opts.package_version;
		package_module = opts.package_module;
	else:
		if not os.path.exists('config.h'):
			print 'Could not find config.h in current directory'
			sys.exit(1)
	
		f = open('config.h', 'r')
		s = f.read()
		f.close()

		key = {}
		key['package'] = '#define PACKAGE_NAME "'
		key['version'] = '#define PACKAGE_VERSION "'
		key['bugreport'] = '#define PACKAGE_BUGREPORT "'

		for line in s.splitlines(1):
			if line.startswith(key['package']):
				p1 = len(key['package'])
				p2 = line.rfind('"')
				p_name = line[p1:p2] 		
			elif line.startswith(key['version']):
				p1 = len(key['version'])
				p2 = line.rfind('"')
				p_version = line[p1:p2] 		
			elif line.startswith(key['bugreport']):
				p2 = line.rfind('"')
				p1 = line.rfind('=') + 1
				p_module = line[p1:p2] 		

		if len(p_name) < 1:
			print 'Could not obtain package name from config.h'
			sys.exit(1)

		if len(p_version) < 1:
			print 'Could not obtain package version from config.h'
			sys.exit(1)

		package_name = p_name;
		package_version = p_version;
		package_module = p_module;

def get_svn_root():
	info = os.popen('svn info --xml').read()

	key = '<root>'
	start = info.find(key)
	if start == -1:
		print 'Could not get Root (start) for subversion details'
		sys.exit(1)

	start += len(key)	
		
	key = '</root>'
	end = info.find(key, start)
	if end == -1:	
		print 'Could not get Root (end) for subversion details'
		sys.exit(1)

	return info[start:end]

def get_svn_url():
	info = os.popen('svn info --xml').read()

	key = '<url>'
	start = info.find(key)
	if start == -1:
		print 'Could not get URL (start) for subversion details'
		sys.exit(1)

	start += len(key)	
		
	key = '</url>'
	end = info.find(key, start)
	if end == -1:	
		print 'Could not get URL (end) for subversion details'
		sys.exit(1)

	return info[start:end]

def get_bugs(tag):
	get_package_info()

	if vc_command == 'cvs':
		cmd = '%s diff %s -r %s ChangeLog' % (vc_command, vc_parameters, tag)
	elif vc_command == 'svn':
		url = get_svn_url()
		root = get_svn_root()

		revision = "%s/tags/%s" % (root, tag)
		if opts.debug: 
			print 'Using SVN root: %s...' % (root) 
			print 'Using SVN diff url1: %s...' % (url) 
			print 'Using SVN diff url2: %s...' % (revision) 

		cmd = '%s diff %s %s/ChangeLog %s/ChangeLog' % (vc_command, vc_parameters, revision, url)
	else:
		print 'Version control system unrecognised, not cvs or svn'
		sys.exit(1)

	bugs = ''
	
	# Pattern to match ChangeLog entry
	exp = '^\+(?P<date>[0-9][0-9][0-9][0-9]\-[0-9][0-9]\-[0-9][0-9]) ' \
		  '(?P<name>.*) <*@*>*'
	changelog_pattern = re.compile(exp, re.S | re.M)

	# Patter to match bug fixers name, e.g.: "#123456 (Martyn Russell)"
	exp = '.*#(?P<bug>[0-9]+)(.*\((?P<name>.*)\))?'
	bugfix_pattern = re.compile(exp, re.S | re.M)

	if opts.debug: 
		print 'Retrieving bug changes since tag: %s...' % (tag) 

	pos = 0
	changes = os.popen(cmd).read()

	while not pos == -1:
		start = pos

		# Find end of first line
		end = changes.find('\n', pos)
		line = changes[pos:end]

		pos = end + 1

		# Try and get the second line
		end = changes.find('\n', pos)
		if not end == -1:
			line = changes[start:end]

		if len(line) < 1:
			break

		# Check this is a change 	
		if not line[0] == '+':
			continue

		# Get committer details
		match = changelog_pattern.match(line)
		if match:
			last_committer = match.group('name')	
			continue

		# Get bug fix details
		match = bugfix_pattern.match(line)
		if not match:
			continue

		bug = match.group('bug')
		name = match.group('name')

		if bug == '':
			continue
		
		if name == None:	
			name = last_committer.strip()
			method = 'cvs user'
		else:
			name = name.replace('\n', '')
			name = name.replace('\t', '')
			name = name.replace('+', ' ')
			name = name.strip()
			method = 'patch'

		# Set name for bug
		bug_names[bug] = name

		if bugs.find(bug) > -1:
			continue

		# Add bug to list
		if not bugs == '':
			bugs = bugs + ','
		bugs = bugs + bug
		
	return bugs

def get_summary(bugs):
	if bugs == '':
		return 'No summary due to no bugs';

	# Bugzilla query to use
	query = 'http://bugzilla.gnome.org/buglist.cgi?ctype=csv' \
		'&bug_status=RESOLVED,CLOSED,VERIFIED' \
		'&resolution=FIXED' \
		'&bug_id='
	query = query + bugs.replace(',', '%2c')

	if opts.debug:
		print 'Retrieving bug information for: %s...' % (bugs)

	f = urllib.urlopen(query)
	s = f.read()
	f.close()

	col_bug_id = -1
	col_description = -1

	reader = csv.reader(s.splitlines(1))
	header = reader.next()
	i = 0

	for col in header:
		if col == 'bug_id':
			col_bug_id = i
		if col == 'short_short_desc':
			col_description = i

		i = i + 1

	if col_bug_id == -1 or col_description == -1:
		print 'Could not identify the bug id or description columns'
		sys.exit()

	summary = ''

	if opts.html:
		summary += '<ul>'
	
	for row in reader:
		bug_number = row[col_bug_id]
		description = row[col_description]
		who = bug_names[bug_number]

		if len(summary) > 0:
			summary += '\n'

		if opts.html:
			link = "http://bugzilla.gnome.org/show_bug.cgi?id=%s" % (bug_number)
			bug = "<a href=\"%s\">#%s</a>" % (link, bug_number)
		else:
			bug = "#%s" % (bug_number)

		text = 'Fixed %s, %s (%s)' % (bug, description, who)

		if opts.html:
			summary += '<li>%s</li>' % (text)
		else: 
			summary += '%s %s' % (format_bullet, text)

	if opts.html:
		summary += '\n</ul>'

	if summary == '':
		summary = 'None'

	return summary

def get_translators(tag, dir):
	get_package_info()

	if vc_command == 'cvs':
		cmd = '%s diff -u -r %s %s/ChangeLog' % (vc_command, tag, dir)
	elif vc_command == 'svn':
		url = get_svn_url()
		root = get_svn_root()

		revision = "%s/tags/%s" % (root, tag)
		if opts.debug: 
			print 'Using SVN root: %s...' % (root) 
			print 'Using SVN diff url1: %s...' % (url) 
			print 'Using SVN diff url2: %s...' % (revision) 

		cmd = '%s diff %s %s/%s/ChangeLog %s/%s/ChangeLog' % (vc_command, vc_parameters, revision, dir, url, dir)
	else:
		print 'Version control system unrecognised, not cvs or svn'
		sys.exit(1)


	translators = {}

	# Pattern to match ChangeLog entry
	exp = '^\+(?P<date>[0-9][0-9][0-9][0-9]\-[0-9][0-9]\-[0-9][0-9]) ' \
		  '(?P<name>.*) <*@*>*'
	changelog_pattern = re.compile(exp, re.S | re.M)

	# Pattern to match language and sponsored name for change, e.g.: 
	# "en_GB.po: Updated by (Martyn Russell)"
	exp = '.*\* (.*/)?(?P<lang>.*).po: (.*\((?P<name>.*)\))?'
	lang_pattern = re.compile(exp, re.S | re.M)

	if opts.debug:
		print 'Retrieving PO changes for %s dir since tag: %s...' % (dir, tag) 

	pos = 0
	changes = os.popen(cmd).read()

	while not pos == -1:
		start = pos

		# Find end of first line
		end = changes.find('\n', pos)
		line = changes[pos:end]

		pos = end + 1

		# Try and get the second line
		end = changes.find('\n', pos)
		if not end == -1:
			line = changes[start:end]

		if len(line) < 1:
			break

		# Check this is a change 	
		if not line[0] == '+':
			continue

		# Get committer details
		match = changelog_pattern.match(line)
		if match:
			last_committer = match.group('name')	
			continue

		# Get bug fix details
		match = lang_pattern.match(line)
		if not match:
			continue

		lang = match.group('lang')
		name = match.group('name')

		if lang == '':
			continue
		
		if name == None:	
			name = last_committer.strip()
		else:
			name = name.replace('\n', '')
			name = name.replace('\t', '')
			name = name.replace('+', ' ')
			name = name.strip()

		if translators.has_key(lang):
			if translators[lang].find(name) > -1:
				continue;	

			translators[lang] += ', ' + name 
		else:
			translators[lang] = name

	summary = ''

	if opts.html:
		summary += '<ul>'
	
	for lang in translators:
		if len(summary) > 0:
			summary += '\n'

		text = 'Updated %s: %s' % (lang, translators[lang])

		if opts.html:
			summary += '<li>%s</li>' % (text)
		else: 
			summary += '%s %s' % (format_bullet, text)

	if opts.html:
		summary += '\n</ul>'

	if summary == '':
		summary = 'None'

	return summary

def get_description():
	get_package_info()

	if opts.debug:
		print 'Retrieving product descripton for %s ...' % (package_name)

	query = 'http://bugzilla.gnome.org/browse.cgi?product=%s' % (package_module)
	f = urllib.urlopen(query)
	s = f.read()
	f.close()

	if len(s) < 1:
		return ''
	
	#
	# HACK ALERT! HACK ALERT!
	#
	# This is likely to change if the Bugzilla page formatting changes, so 
	# we put a lot of debugging in here.

	s1 = '<p><i>'
	i = s.find(s1)
	if i == -1:
		if opts.debug:
			print 'Could not find string "%s"' % (s1) 
	
		return ''
	
	start = i + len(s1)

	s2 = '</i></p>'
	end = s.find(s2, i + 1)
	if end == -1:
		if opts.debug:
			print 'Could not find string "%s"' % (s2) 
	
		return ''
	
	# Get description
	description = s[start:end]

	return description

def get_website():
	get_package_info()

	if opts.debug:
		print 'Retrieving product website for %s ...' % (package_name)

	query = 'http://bugzilla.gnome.org/browse.cgi?product=%s' % (package_module)
	f = urllib.urlopen(query)
	s = f.read()
	f.close()

	if len(s) < 1:
		return ''

	# Get Homepage
	s1 = "GNOME SVN"
	i = s.find(s1)
	if i == -1:
		if opts.debug:
			print 'Could not find string "%s"' % (s1) 
	
		return ''

	s1 = "href"
	i = s.find(s1, i)
	if i == -1:
		if opts.debug:
			print 'Could not find string "%s"' % (s1) 
	
		return ''
	
	start = i + 6

	s2 = '">'
	end = s.find(s2, start)
	if end == -1:
		if opts.debug:
			print 'Could not find string "%s"' % (s2) 
	
		return ''
	
	return s[start:end]

def get_default_template():
	if opts.html:
		return template_in_html

	return template

def get_news_items():
	f = open ('NEWS', 'r')
	s = f.read()
	f.close()
	start = s.find ('NEW in %s' % package_version)
	#skip the '========='
	start = s.find ('\n', start) + 1
	#go to the next line
	start = s.find ('\n', start) + 1
	#stop at the last news entry
	end = s.find ('NEW in %s' % opts.revision, start) - 1
	return s[start:end]

def create_release_note(tag, template_file):
	# Open template file
	if template_file == '' or template_file == 'DEFAULT':
		if opts.debug:
			print 'Using DEFAULT template'

		s = get_default_template()
	else:
		if opts.debug:
			print 'Using template file "%s"' % (template_file)

		f = open(template_file, 'r')
		s = f.read()
		f.close()

	if len(s) < 1: 
		print 'Template file was empty or does not exist'
		sys.exit(1)

	# Check we have everything
	if s.find('$download') == -1:
		print 'Could not find "$download" in template'
		sys.exit(1)

	if s.find('$news') == -1:
		print 'Could not find "$news" in template'
		sys.exit(1)

	if s.find('$fixed') == -1:
		print 'Could not find "$fixed" in template'
		sys.exit(1)

	if s.find('$translations') == -1:
		print 'Could not find "$translations" in template'
		sys.exit(1)

	if s.find('$help_translations') == -1:
		print 'Could not find "$help_translations" in template'
		sys.exit(1)

	# Get date for footer
	today = datetime.date.today()
	date = today.strftime(format_date) 

	# Get package name and version
	get_package_info()

	# Set up variables
	name = package_name
	version = package_version

	bugs = get_bugs(tag)

	download = 'http://download.gnome.org/sources/%s/%s/' % (package_name.lower(), 
								 package_version[0:3])

	# Get an MD5 sum of the tarballs.
	md5sums = ''
	
	cmd = 'md5sum %s-%s.tar.gz' % (package_name.lower(), package_version)
	md5sums += os.popen(cmd).read()

	cmd = 'md5sum %s-%s.tar.bz2' % (package_name.lower(), package_version)
	md5sums += os.popen(cmd).read()

	if opts.html:
		md5sums = md5sums.replace('\n', '<br>\n')
	
	about = get_description()
	website = get_website()

	news = get_news_items()

	fixed = get_summary(bugs)
	translations = get_translators(tag, po_dir)
	help_translations = get_translators(tag, help_dir)
	
	footer = '%s\n%s team' % (date, package_name)

	if opts.html:
		footer = footer.replace('\n', '<br>\n')
		footer = '<p>%s</p>' % footer

	# Substitute variables
	t = Template(s)
	text = t.substitute(locals())

	return text

def create_release_email(to, tag, template_file):
	release_note = create_release_note(tag, template_file)

	t = Template(release_note)
	text = t.substitute(locals())

	body = ''

 	for line in text.splitlines():
		body = body + line + '%0d'

	# Get package name and version
	get_package_info()

	subject = 'ANNOUNCE: %s %s released' % (package_name, package_version)

	url = 'mailto:%s?subject=%s&body=%s' % (to, subject, body)
	
	return url;

def upload_tarball():
	get_package_info()

	# This is the tarball we are going to upload
	username = opts.upload
	tarball = '%s-%s.tar.gz' % (package_name.lower(), package_version)

	print 'Attempting to upload tarball: %s to master.gnome.org...' % (tarball)
		
	cmd = 'scp %s %s@%s:' % (tarball, username, upload_server)
	fp = os.popen(cmd)
	retval = fp.read()
	status = fp.close()

	if status and (not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0):
		print 'Unable to upload your tarball'
	else:
		print 'Sucessfully uploaded tarball'

	print 'Attempting to install-module using tarball: %s...' % (tarball)
		
	cmd = 'ssh %s@%s install-module -u %s' % (username, upload_server, tarball)
	success = os.popen(cmd).read()

	# Make sure we check the return value
	fp = os.popen(cmd)
	retval = fp.read()
	status = fp.close()

	if status and (not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0):
		print 'Unable to install module'
	else:
		print 'Sucessfully installed module'


def get_news():
	get_package_info()

	bugs = get_bugs(opts.revision)
	if len(bugs) < 1:
		print 'No bugs were found to update the NEWS file with'
		sys.exit()

	fixed = get_summary(bugs)
	if len(fixed) < 1:
		print 'No summary was available to update the NEWS file with'
		sys.exit()

	translations = get_translators(opts.revision, po_dir)
	help_translations = get_translators(opts.revision, help_dir)
	
	version = package_version
	news = get_news_items()
	t = Template(template_update_news)
	output = t.substitute(locals())

	f = open('NEWS', 'r')
	s = f.read()
	f.close()

	#We replace the current NEWS with our one which includes
	#bugs fixed, and translations. Therefor we need to skip over
	#all content up until the previous revision
	start = s.find ('NEW in %s' % opts.revision) - 1

	output += s[start:]
	print output

def tag_svn():
	get_package_info()

	new_version = opts.tag[opts.tag.find ('_')+1:].replace ('_', '.')
	url1 = get_svn_url()
	url2 = get_svn_root() + '/tags/' + opts.tag

	cmd = 'svn copy %s %s -m "Tagged for release %s."' % (url1, url2, new_version)

	if opts.debug:
		print 'Tagging using command: ' + cmd

	success = os.popen(cmd).read()

	# Make sure we check the return value
	fp = os.popen('{ %s; } 2>&1' % cmd, 'r')
	retval = fp.read()
	status = fp.close()

	if status and (not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0):
		print 'Unable to tag SVN'
	else:
		print 'Sucessfully tagged SVN'

#
# Start
#
usage = "usage: %s -r <revision or tag> [options]\n" \
	"       %s --help" % (sys.argv[0], sys.argv[0])

popt = optparse.OptionParser(usage)
popt.add_option('-v', '--version',
		action = 'count', 
		dest = 'version',
		help = 'show version information')
popt.add_option('-d', '--debug',
		action = 'count', 
		dest = 'debug',
		help = 'show additional debugging')
popt.add_option('-l', '--html',
		action = 'count', 
		dest = 'html',
		help = 'write output in HTML')
popt.add_option('-c', '--confirm',
		action = 'count', 
		dest = 'confirm',
		help = 'this is required for some actions as confirmation')
popt.add_option('-b', '--get-bugs',
		action = 'count', 
		dest = 'get_bugs', 
		help = 'get a list of bugs fixed')
popt.add_option('-s', '--get-summary',
		action = 'count', 
		dest = 'get_summary',
		help = 'get summary of bugs from Bugzilla')
popt.add_option('-t', '--get-translators',
		action = 'count', 
		dest = 'get_translators',
		help = 'get translation updates')
popt.add_option('-o', '--get-manual-translators',
		action = 'count', 
		dest = 'get_manual_translators',
		help = 'get manual translation updates')
popt.add_option('-e', '--get-description',
		action = 'count', 
		dest = 'get_description',
		help = 'get the description in bugzilla for this product')
popt.add_option('-i', '--get-website',
		action = 'count', 
		dest = 'get_website',
		help = 'get the website in bugzilla for this product')
popt.add_option('-I', '--get-news-items',
		action = 'count', 
		dest = 'get_news_items',
		help = 'get the new items from the NEWS file')
popt.add_option('-N', '--get-news',
		action = 'count', 
		dest = 'get_news',
		help = 'get the complete NEWS, including bugs fixed and translations')
popt.add_option('-a', '--create-release-note',
		action = 'count',
		dest = 'create_release_note',
		help = 'create a release note (can be used with -n)')
popt.add_option('-n', '--release-note-template',
		action = 'store', 
		dest = 'release_note_template',
		help = 'file to use for release note template or "DEFAULT"')
popt.add_option('-m', '--create-release-email',
		action = 'store',
		dest = 'create_release_email',
		help = 'who to address the mail to (can be used with -n)')
popt.add_option('-u', '--upload',
		action = 'store', 
		dest = 'upload',
		help = 'user name to use when uploading tarball to master.gnome.org')
popt.add_option('-g', '--tag',
		action = 'store', 
		dest = 'tag',
		help = 'Tag to add in SVN')
popt.add_option('-r', '--revision',
		action = 'store', 
		dest = 'revision',
		help = 'revision or tag to use with -s, -t, -o and -b')
popt.add_option('-p', '--package-name',
		action = 'store', 
		dest = 'package_name',
		help = 'the package name (if not using config.h)')
popt.add_option('-V', '--package-version',
		action = 'store', 
		dest = 'package_version',
		help = 'the package version (if not using config.h)')
popt.add_option('-M', '--package-module',
		action = 'store', 
		dest = 'package_module',
		help = 'the package module name in bugzilla (if not using config.h)')

errors = False
need_tag = False

(opts, args) = popt.parse_args()

if opts.version:
	print '%s %s\n%s\n' % (script_name, script_version, script_about)
	sys.exit()

if not opts.get_bugs and not opts.get_summary and \
   not opts.get_translators and not opts.get_manual_translators and \
   not opts.release_note_template and not opts.create_release_note and \
   not opts.create_release_email and not opts.upload and \
   not opts.get_description and not opts.get_website and \
   not opts.tag and not opts.get_news and not opts.get_news_items:
	print 'No option specified'
	print usage
	sys.exit()

if opts.get_bugs or opts.get_summary or \
   opts.get_translators or opts.get_manual_translators or \
   opts.create_release_note or opts.create_release_email or \
   opts.get_news or opts.get_news_items:
	need_tag = True

if need_tag and not opts.revision:
	print 'No tag specified'
	print usage
	sys.exit()

if opts.upload and not opts.confirm:
	print 'Uploading WILL *INSTALL* your tarball with install-module!!'
	print 'Are you sure you want to continue?'
	print
	print 'To continue, you must supply the --confirm option'
	sys.exit()

if opts.tag and not opts.confirm:
	print 'This will create a new tag on your SVN repository!!'
	print 'Are you sure you want to continue?'
	print
	print 'To continue, you must supply the --confirm option'
	sys.exit()

if opts.get_bugs:
	bugs = get_bugs(opts.revision)
	if len(bugs) < 1:
		print 'No bugs found fixed'
		sys.exit(0)

	if opts.debug:
		print '\nBugs:'

	print bugs

if opts.get_summary:
	bugs = get_bugs(opts.revision)
	if len(bugs) < 1:
		print 'No bugs found fixed'
		sys.exit(0)

	summary = get_summary(bugs)
	if len(summary) < 1:
		print 'Could not get summary for bug fixes: %s' % (bugs)
		sys.exit(0)

		if opts.debug:
			print '\nSummary:' 

	print summary

if opts.get_translators:
	translators = get_translators(opts.revision, po_dir)
	if len(translators) < 1:
		print 'No translation updates found'
		sys.exit(0)

	if opts.debug:
		print '\nTranslators:' 

	print translators

if opts.get_manual_translators:
	translators = get_translators(opts.revision, help_dir)
	if len(translators) < 1:
		print 'No manual translation updates found'
		sys.exit(0)

	if opts.debug:
		print '\nManual Translators:' 

	print translators

if opts.get_description:
	description = get_description()
	if len(description) < 1:
		print 'No description was found in bugzilla'
		sys.exit(0)

	if opts.debug:
		print '\nDescription:'

	print description

if opts.get_website:
	website = get_website()
	if len(website) < 1:
		print 'No website was found in bugzilla'
		sys.exit(0)

	if opts.debug:
		print '\nWebsite:'

	print website

if opts.create_release_note:
	if opts.release_note_template:
		release_note = create_release_note(opts.revision, 
						   opts.release_note_template)
	else:
		release_note = create_release_note(opts.revision, 
						   'DEFAULT')


	if opts.debug:
		print '\nRelease Note:' 

	print release_note
	
if opts.create_release_email:
	if opts.release_note_template:
		url = create_release_email(opts.create_release_email, 
					   opts.revision, 
					   opts.release_note_template)
	else:
		url = create_release_email(opts.create_release_email, 
					   opts.revision, 
					   'DEFAULT')

	if opts.debug:
		print '\nCreating email...' 

	gnomevfs.url_show(url)
	
if opts.upload:
	upload_tarball()

if opts.get_news_items:
	if opts.debug:
		print '\nNews Items:'
	print get_news_items()

if opts.get_news:
	if opts.debug:
		print '\nNews:'
	print get_news()

if opts.tag:
	tag_svn()

