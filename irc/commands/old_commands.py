###### 
###### NOTE:
###### This is an old commands file from the previous version of EarwigBot.
###### It is not used by the new EarwigBot and is simply here for reference
###### when developing new commands.
###### 
# -*- coding: utf-8  -*-
### EarwigBot

## Import basics.
import sys, socket, string, time, codecs, os, traceback, thread, re, urllib, web, math, unicodedata

## Import our functions.
import config

## Set up constants.
HOST, PORT, NICK, IDENT, REALNAME, CHANS, REPORT_CHAN, WELCOME_CHAN, HOST2, CHAN2, OWNER, ADMINS, ADMINS_R, PASS = config.host, config.port, config.nick, config.ident, config.realname, config.chans, config.report_chan, config.welcome_chan, config.host2, config.chan2, config.owner, config.admins, config.admin_readable, config.password

def get_commandList():
	return {'quiet': 'quiet',
	'welcome': 'welcome',
	'greet': 'welcome',
	'linker': 'linker',
	'auth': 'auth',
	'access': 'access',
	'join': 'join',
	'part': 'part',
	'restart': 'restart',
	'quit': 'quit',
	'die': 'quit',
	'msg': 'msg',
	'me': 'me',
	'calc': 'calc',
	'dice': 'dice',
	'tock': 'tock',
	'beats': 'beats',
	'copyvio': 'copyvio', 
	'copy': 'copyvio',
	'copyright': 'copyvio',
	'dict': 'dictionary',
	'dictionary': 'dictionary',
	'ety': 'etymology',
	'etymology': 'etymology',
	'lang': 'langcode',
	'langcode': 'langcode',
	'num': 'number',
	'number': 'number',
	'count': 'number',
	'c': 'number',
	'nick': 'nick',
	'op': 'op',
	'deop': 'deop',
	'voice': 'voice',
	'devoice': 'devoice',
	'pend': 'pending',
	'pending': 'pending',
	'sub': 'submissions',
	'submissions': 'submissions',
	'praise': 'praise',
	'leonard': 'leonard',
	'groovedog': 'groovedog',
	'earwig': 'earwig',
	'macmed': 'macmed',
	'cubs197': 'cubs197',
	'sparksboy': 'sparksboy',
	'tim_song': 'tim_song',
	'tim': 'tim_song',
	'blurpeace': 'blurpeace',
	'sausage': 'sausage',
	'mindstormskid': 'mindstormskid',
	'mcjohn': 'mcjohn',
	'fetchcomms': 'fetchcomms',
	'trout': 'trout',
	'kill': 'kill',
	'destroy': 'kill',
	'murder': 'kill',
	'fish': 'fish',
	'report': 'report',
	'commands': 'commands',
	'help': 'help',
	'doc': 'help',
	'documentation': 'help',
	'mysql': 'mysql',
	'remind': 'reminder',
	'reminder': 'reminder',
	'notes': 'notes',
	'note': 'notes',
	'about': 'notes',
	'data': 'notes',
	'database': 'notes',
	'hash': 'hash',
	'lookup': 'lookup',
	'ip': 'lookup'
	}

def main(command, line, line2, nick, chan, host, auth, notice, say, reply, s):
	try:
		parse(command, line, line2, nick, chan, host, auth, notice, say, reply, s)
	except Exception:
		trace = traceback.format_exc() # Traceback.
		print trace # Print.
		lines = list(reversed(trace.splitlines())) # Convert lines to process traceback....
		report2 = [lines[0].strip()]
		for line in lines: 
			line = line.strip()
			if line.startswith('File "/'): 
				report2.append(line[0].lower() + line[1:])
				break
		else: report2.append('source unknown')
		say(report2[0] + ' (' + report2[1] + ')', chan)

def parse(command, line, line2, nick, chan, host, auth, notice, say, reply, s):
	authy = auth(host)
	if command == "access":
		a = 'The bot\'s owner is "%s".' % OWNER
		b = 'The bot\'s admins are "%s".' % ', '.join(ADMINS_R)
		reply(a, chan, nick)
		reply(b, chan, nick)
		return
	if command == "join":
		if authy == "owner" or authy == "admin":
			try:
				channel = line2[4]
			except Exception:
				channel = chan
			s.send("JOIN %s\r\n" % channel)
		else:
			reply("You aren't authorized to use that command.", chan, nick)
		return
	if command == "part":
		if authy == "owner" or authy == "admin":
			try:
				channel = line2[4]
			except Exception:
				channel = chan
			s.send("PART %s\r\n" % channel)
		else:
			reply("You aren't authorized to use that command.", chan, nick)
		return
	if command == "restart":
		import thread
		if authy == "owner":
			s.send("QUIT\r\n")
			time.sleep(5)
			os.system("nice -15 python main.py")
			exit()
		else:
			reply("Only the owner, %s, can stop the bot. This incident will be reported." % OWNER, chan, nick)
		return
	if command == "quit" or command == "die":
		if authy != "owner":
			if command != "suicide":
				reply("Only the owner, %s, can stop the bot. This incident will be reported." % OWNER, chan, nick)
			else:
				say("\x01ACTION hands %s a gun... have fun :D\x01" % nick, nick)
		else:
			if command == "suicide":
				say("\x01ACTION stabs himself with a knife.\x01", chan)
				time.sleep(0.2)
			try:
				s.send("QUIT :%s\r\n" % ' '.join(line2[4:]))
			except Exception:
				s.send("QUIT\r\n")
			__import__('os')._exit(0)
		return
	if command == "msg":
		if authy == "owner" or authy == "admin":
			say(' '.join(line2[5:]), line2[4])
		else:
			reply("You aren't authorized to use that command.", chan, nick)
		return
	if command == "me":
		if authy == "owner" or authy == "admin":
			say("\x01ACTION %s\x01" % ' '.join(line2[5:]), line2[4])
		else:
			reply("You aren't authorized to use that command.", chan, nick)
		return
	if command == "calc":
		r_result = re.compile(r'(?i)<A NAME=results>(.*?)</A>')
		r_tag = re.compile(r'<\S+.*?>')
		subs = [
				(' in ', ' -> '), 
				(' over ', ' / '), 
				(u'¬£', 'GBP '), 
				(u'‚Ç¨', 'EUR '), 
				('\$', 'USD '), 
				(r'\bKB\b', 'kilobytes'), 
				(r'\bMB\b', 'megabytes'), 
				(r'\bGB\b', 'kilobytes'), 
				('kbps', '(kilobits / second)'), 
				('mbps', '(megabits / second)')
		]
		try:
			q = ' '.join(line2[4:])
		except Exception:
			say("0?", chan)
			return
		query = q[:]
		for a, b in subs: 
			query = re.sub(a, b, query)
		query = query.rstrip(' \t')

		precision = 5
		if query[-3:] in ('GBP', 'USD', 'EUR', 'NOK'): 
			precision = 2
		query = web.urllib.quote(query.encode('utf-8'))

		uri = 'http://futureboy.us/fsp/frink.fsp?fromVal='
		bytes = web.get(uri + query)
		m = r_result.search(bytes)
		if m: 
			result = m.group(1)
			result = r_tag.sub('', result) # strip span.warning tags
			result = result.replace('&gt;', '>')
			result = result.replace('(undefined symbol)', '(?) ')

			if '.' in result: 
				try: result = str(round(float(result), precision))
				except ValueError: pass

			if not result.strip(): 
				result = '?'
			elif ' in ' in q: 
				result += ' ' + q.split(' in ', 1)[1]

			say(q + ' = ' + result[:350], chan)
		else: reply("Sorry, can't calculate that.", chan, nick)
		return
	if command == "dice":
		import random
		try:
			set = range(int(line2[4]), int(line2[5]) + 1)
		except Exception:
			set = range(1, 7)
		num = random.choice(set)
		reply("You rolled a %s." % num, chan, nick)
		if len(set) < 30:
			say("Set consisted of %s." % set, nick)
		else:
			say("Set consisted of %s... and %s others." % (set[:30], len(set) - 30), nick)
		return
	if command == "tock":
		u = urllib.urlopen('http://tycho.usno.navy.mil/cgi-bin/timer.pl')
		info = u.info()
		u.close()
		say('"' + info['Date'] + '" - tycho.usno.navy.mil', chan)
		return
	if command == "beats":
		beats = ((time.time() + 3600) % 86400) / 86.4
		beats = int(math.floor(beats))
		say('@%03i' % beats, chan)
		return
	if command == "copyvio" or command == "copy" or command == "copyright":
		url = "http://en.wikipedia.org/wiki/User:EarwigBot/AfC copyvios"
		query = urllib.urlopen(url)
		data = query.read()
		url = "http://toolserver.org/~earwig/earwigbot/pywikipedia/error.txt"
		query = urllib.urlopen(url)
		data2 = query.read()
		if "critical" in data2:
			text = "AfC copyvio situation is CRITICAL: Major disaster."
		elif "exceed" in data2:
			text = "AfC copyvio situation is CRITICAL: Queries exceeded error."
		elif "spam" in data2:
			text = "AfC copyvio situation is CRITICAL: Spamfilter error."
		elif "<h3>" in data:
			text = "AfC copyvio situation is BAD: Unsolved copyvios at [[User:EarwigBot/AfC copyvios]]"
		else:
			text = "AfC copyvio situation is OK: OK."
		reply(text, chan, nick)
		return
	if command == "dict" or command == "dictionary":
		def trim(thing): 
			if thing.endswith('&nbsp;'): 
				thing = thing[:-6]
			return thing.strip(' :.')
		r_li = re.compile(r'(?ims)<li>.*?</li>')
		r_tag = re.compile(r'<[^>]+>')
		r_parens = re.compile(r'(?<=\()(?:[^()]+|\([^)]+\))*(?=\))')
		r_word = re.compile(r'^[A-Za-z0-9\' -]+$')
		uri = 'http://encarta.msn.com/dictionary_/%s.html'
		r_info = re.compile(r'(?:ResultBody"><br /><br />(.*?)&nbsp;)|(?:<b>(.*?)</b>)')
		try:
			word = line2[4]
		except Exception:
			reply("Please enter a word.", chan, nick)
			return
		word = urllib.quote(word.encode('utf-8'))
		bytes = web.get(uri % word)
		results = {}
		wordkind = None
		for kind, sense in r_info.findall(bytes): 
			kind, sense = trim(kind), trim(sense)
			if kind: wordkind = kind
			elif sense: 
				results.setdefault(wordkind, []).append(sense)
		result = word.encode('utf-8') + ' - '
		for key in sorted(results.keys()): 
			if results[key]: 
				result += (key or '') + ' 1. ' + results[key][0]
				if len(results[key]) > 1: 
					result += ', 2. ' + results[key][1]
				result += '; '
		result = result.rstrip('; ')
		if result.endswith('-') and (len(result) < 30): 
			reply('Sorry, no definition found.', chan, nick)
		else: say(result, chan)
		return
	if command == "ety" or command == "etymology":
		etyuri = 'http://etymonline.com/?term=%s'
		etysearch = 'http://etymonline.com/?search=%s'
		r_definition = re.compile(r'(?ims)<dd[^>]*>.*?</dd>')
		r_tag = re.compile(r'<(?!!)[^>]+>')
		r_whitespace = re.compile(r'[\t\r\n ]+')
		abbrs = [
			'cf', 'lit', 'etc', 'Ger', 'Du', 'Skt', 'Rus', 'Eng', 'Amer.Eng', 'Sp', 
			'Fr', 'N', 'E', 'S', 'W', 'L', 'Gen', 'J.C', 'dial', 'Gk', 
			'19c', '18c', '17c', '16c', 'St', 'Capt', 'obs', 'Jan', 'Feb', 'Mar', 
			'Apr', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'c', 'tr', 'e', 'g'
		]
		t_sentence = r'^.*?(?<!%s)(?:\.(?= [A-Z0-9]|\Z)|\Z)'
		r_sentence = re.compile(t_sentence % ')(?<!'.join(abbrs))
		def unescape(s): 
			s = s.replace('&gt;', '>')
			s = s.replace('&lt;', '<')
			s = s.replace('&amp;', '&')
			return s
		def text(html): 
			html = r_tag.sub('', html)
			html = r_whitespace.sub(' ', html)
			return unescape(html).strip()
		try:
			word = line2[4]
		except Exception:
			reply("Please enter a word.", chan, nick)
			return
		def ety(word):
			if len(word) > 25: 
				raise ValueError("Word too long: %s[...]" % word[:10])
			word = {'axe': 'ax/axe'}.get(word, word)
			bytes = web.get(etyuri % word)
			definitions = r_definition.findall(bytes)
			if not definitions: 
				return None
			defn = text(definitions[0])
			m = r_sentence.match(defn)
			if not m: 
				return None
			sentence = m.group(0)
			try: 
				sentence = unicode(sentence, 'iso-8859-1')
				sentence = sentence.encode('utf-8')
			except: pass
			maxlength = 275
			if len(sentence) > maxlength: 
				sentence = sentence[:maxlength]
				words = sentence[:-5].split(' ')
				words.pop()
				sentence = ' '.join(words) + ' [...]'
			sentence = '"' + sentence.replace('"', "'") + '"'
			return sentence + ' - ' + (etyuri % word)
		try:
			result = ety(word.encode('utf-8'))
		except IOError: 
			msg = "Can't connect to etymonline.com (%s)" % (etyuri % word)
			reply(msg, chan, nick)
			return
		except AttributeError: 
			result = None
		if result is not None: 
			reply(result, chan, nick)
		else: 
			uri = etysearch % word
			msg = 'Can\'t find the etymology for "%s". Try %s' % (word, uri)
			reply(msg, chan, nick)
		return
	if command == "num" or command == "number" or command == "count" or command == "c":
		try:
			params = string.lower(line2[4])
		except Exception:
			params = False
		if params == "old" or params == "afc" or params == "a":
			number = unicode(int(len(re.findall("title=", urllib.urlopen("http://en.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Category:Pending_AfC_submissions&cmlimit=500").read()))) - 2)
			reply("There are currently %s pending AfC submissions." % number, chan, nick)
		elif params == "redirect" or params == "redir" or params == "redirs" or params == "redirects" or params == "r":
			redir_data = urllib.urlopen("http://en.wikipedia.org/w/index.php?title=Wikipedia:Articles_for_creation/Redirects").read()
			redirs = (string.count(redir_data, "<h2>") - 1) - (string.count(redir_data, '<table class="navbox collapsible collapsed" style="text-align: left; border: 0px; margin-top: 0.2em;">'))
			reply("There are currently %s open redirect requests." % redirs, chan, nick)
		elif params == "files" or params == "ffu" or params == "file" or params == "image" or params == "images" or params == "ifu" or params == "f":
			file_data = re.sub("<h2>Contents</h2>", "", urllib.urlopen("http://en.wikipedia.org/w/index.php?title=Wikipedia:Files_for_upload").read())
			files = (string.count(file_data, "<h2>") - 1) - (string.count(file_data, '<table class="navbox collapsible collapsed" style="text-align: left; border: 0px; margin-top: 0.2em;">'))
			reply("There are currently %s open file upload requests." % files, chan, nick)
		elif params == "aggregate" or params == "agg":
			subs = unicode(int(len(re.findall("title=", urllib.urlopen("http://en.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Category:Pending_AfC_submissions&cmlimit=500").read()))) - 2)
			redir_data = urllib.urlopen("http://en.wikipedia.org/w/index.php?title=Wikipedia:Articles_for_creation/Redirects").read()
			file_data = re.sub("<h2>Contents</h2>", "", urllib.urlopen("http://en.wikipedia.org/w/index.php?title=Wikipedia:Files_for_upload").read())
			redirs = (string.count(redir_data, "<h2><span class=\"editsection\">")) - (string.count(redir_data, '<table class="navbox collapsible collapsed" style="text-align: left; border: 0px; margin-top: 0.2em;">'))
			files = (string.count(file_data, "<h2>") - 1) - (string.count(file_data, '<table class="navbox collapsible collapsed" style="text-align: left; border: 0px; margin-top: 0.2em;">'))
			aggregate = (int(subs) * 5) + (int(redirs) * 2) + (int(files) * 2)
			if aggregate == 0:
				stat = "clear"
			elif aggregate < 60:
				stat = "almost clear"
			elif aggregate < 125:
				stat = "small backlog"
			elif aggregate < 175:
				stat = "average backlog"
			elif aggregate < 250:
				stat = "backlogged"
			elif aggregate < 300:
				stat = "heavily backlogged"
			else:
				stat = "severely backlogged"
			reply("Aggregate is currently %s (%s)." % (aggregate, stat), chan, nick)
		else:
			subs = unicode(int(len(re.findall("title=", urllib.urlopen("http://en.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Category:Pending_AfC_submissions&cmlimit=500").read()))) - 2)
			redir_data = urllib.urlopen("http://en.wikipedia.org/w/index.php?title=Wikipedia:Articles_for_creation/Redirects").read()
			file_data = re.sub("<h2>Contents</h2>", "", urllib.urlopen("http://en.wikipedia.org/w/index.php?title=Wikipedia:Files_for_upload").read())
			redirs = (string.count(redir_data, "<h2><span class=\"editsection\">")) - (string.count(redir_data, '<table class="navbox collapsible collapsed" style="text-align: left; border: 0px; margin-top: 0.2em;">'))
			files = (string.count(file_data, "<h2>") - 1) - (string.count(file_data, '<table class="navbox collapsible collapsed" style="text-align: left; border: 0px; margin-top: 0.2em;">'))
			reply("There are currently %s pending submissions, %s open redirect requests, and %s open file upload requests." % (subs, redirs, files), chan, nick)
		return
	if command == "nick":
		if authy == "owner":
			try:
				new_nick = line2[4]
			except Exception:
				reply("Please specify a nick to change to.", chan, nick)
				return
			s.send("NICK %s\r\n" % new_nick)
		else:
			reply("You aren't authorized to use that command.", chan, nick)
		return
	if command == "op" or command == "deop" or command == "voice" or command == "devoice":
		if authy == "owner" or authy == "admin":
			try:
				user = line2[4]
			except Exception:
				user = nick
			say("%s %s %s" % (command, chan, user), "ChanServ")
		else:
			reply("You aren't authorized to use that command.", chan, nick)
		return
	if command == "pend" or command == "pending":
		say("Pending submissions status page: <http://en.wikipedia.org/wiki/WP:AFC/S>.", chan)
		say("Pending submissions category: <http://en.wikipedia.org/wiki/Category:Pending_AfC_submissions>.", chan)
		return
	if command == "sub" or command == "submissions":
		try:
			number = int(line2[4])
		except Exception:
			reply("Please enter a number.", chan, nick)
			return
		do_url = False
		try:
			if "url" in line2[5:]: do_url = True
		except Exception:
			pass
		url = "http://en.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Category:Pending_AfC_submissions&cmlimit=500&cmsort=timestamp"
		query = urllib.urlopen(url)
		data = query.read()
		pages = re.findall("title=&quot;(.*?)&quot;", data)
		try:
			pages.remove("Wikipedia:Articles for creation/Redirects")
		except Exception:
			pass
		try:
			pages.remove("Wikipedia:Files for upload")
		except Exception:
			pass
		pages.reverse()
		pages = pages[:number]
		if not do_url:
			s = string.join(pages, "]], [[")
			s = "[[%s]]" % s
		else:
			s = string.join(pages, ">, <http://en.wikipedia.org/wiki/")
			s = "<http://en.wikipedia.org/wiki/%s>" % s
			s = re.sub(" ", "_", s)
			s = re.sub(">,_<", ">, <", s)
		report = "\x02First %s pending AfC submissions:\x0F %s" % (number, s)
		say(report, chan)
		return
	if command == "praise" or command == "leonard" or command == "groovedog" or command == "earwig" or command == "macmed" or command == "cubs197" or command == "sparksboy" or command == "tim_song" or command == "tim" or command == "sausage" or command == "mindstormskid" or command == "mcjohn" or command == "fetchcomms" or command == "blurpeace":
		bad = False
		if command == "leonard":
			special = "AfC redirect reviewer"
			user = "Leonard^Bloom"
		elif command == "groovedog":
			special = "heh"
			user = "GrooveDog"
		elif command == "earwig":
			special = "Python programmer"
			user = "Earwig"
		elif command == "macmed":
			special = "CSD tagger"
			user = "MacMed"
		elif command == "mindstormskid":
			special = "Lego fanatic"
			user = "MindstormsKid"
		elif command == "cubs197":
			special = "IRC dude"
			user = "Cubs197"
		elif command == "sparksboy":
			special = "pet owner"
			user = "SparksBoy"
		elif command == "tim_song" or command == "tim":
			special = "JavaScript programmer"
			user = "Tim_Song"
		elif command == "sausage":
			special = "helper"
			user = "chzz"
		elif command == "mcjohn":
			special = "edit summary writer"
			user = "McJohn"
		elif command == "fetchcomms":
			special = "n00b"
			user = "Fetchcomms"
		elif command == "blurpeace":
			special = "Commons admin"
			user = "Blurpeace"
		else:
			say("Only a true fool would use that command, %s." % nick, chan)
			# say("The users who you can praise are: Leonard^Bloom, GrooveDog, Earwig, MacMed, Cubs197, SparksBoy, MindstormsKid, Chzz, McJohn, Tim_Song, Fetchcomms, and Blurpeace.", chan)
			return
		if not bad:
			say("\x02%s\x0F is the bestest %s evah!" % (user, special), chan)
		if bad:
			say("\x02%s\x0F is worstest %s evah!" % (user, special), chan)
		return
	if command == "trout":
		try:
			user = line2[4]
			user = ' '.join(line2[4:])
		except Exception:
			reply("Hahahahahahahaha...", chan, nick)
			return
		normal = unicodedata.normalize('NFKD', unicode(string.lower(user)))
		if "itself" in normal:
			reply("I'm not that stupid ;)", chan, nick)
			return
		elif "earwigbot" in normal:
			reply("I'm not that stupid ;)", chan, nick)
		elif "earwig" not in normal and "ear wig" not in normal:
			text = 'slaps %s around a bit with a large trout.' % user
			msg = '\x01ACTION %s\x01' % text
			say(msg, chan)
		else:
			reply("I refuse to hurt anything with \"Earwig\" in its name :P", chan, nick)
		return
	if command == "kill" or command == "destroy" or command == "murder":
		reply("Who do you think I am? The Mafia?", chan, nick)
		return
	if command == "fish":
		try:
			user = line2[4]
			fish = ' '.join(line2[5:])
		except Exception:
			reply("Hahahahahahahaha...", chan, nick)
			return
		normal = unicodedata.normalize('NFKD', unicode(string.lower(user)))
		if "itself" in normal:
			reply("I'm not that stupid ;)", chan, nick)
			return
		elif "earwigbot" in normal:
			reply("I'm not that stupid ;)", chan, nick)
		elif "earwig" not in normal and "ear wig" not in normal:
			text = 'slaps %s around a bit with a %s.' % (user, fish)
			msg = '\x01ACTION %s\x01' % text
			say(msg, chan)
		else:
			reply("I refuse to hurt anything with \"Earwig\" in its name :P", chan, nick)
		return
	if command == "report":
		def find_status(name="", talk=False):
			enname = re.sub(" ", "_", name)
			if talk == True:
				enname = "Wikipedia_talk:Articles_for_creation/%s" % enname
				if talk == False:
					enname = "Wikipedia:Articles_for_creation/%s" % enname
				url = "http://en.wikipedia.org/w/api.php?action=query&titles=%s&prop=revisions&rvprop=content" % enname
				query = urllib.urlopen(url)
				data = query.read()
				status = ""
				if "{{AFC submission|D" in data or "{{AFC submission|d" in data:
					reason = re.findall("(D|d)\|(.*?)\|", data)
					if reason[0][1] != "reason":
						status = "Declined, reason is '%s'" % reason[0][1]
					if reason[0][1] == "reason":
						status = "Declined, reason is a custom reason"
				if "{{AFC submission|H" in data or "{{AFC submission|h" in data:
					reason = re.findall("(H|h)\|(.*?)\|", data)
					if reason[0][1] != "reason":
						status = "Held, reason is '%s'" % reason[0][1]
					if reason[0][1] == "reason":
						status = "Held, reason is a custom reason"
				if "{{AFC submission||" in data:
					status = "Pending"
				if "{{AFC submission|R" in data or "{{AFC submission|r" in data:
					status = "Reviewing"
				if not status:
					exist = exists(name=enname)
					if exist == True:
						status = "Accepted"
					if exist == False:
						status = "Not found"
				return status
		def exists(name=""):
			url = "http://en.wikipedia.org/wiki/%s" % name
			query = urllib.urlopen(url)
			data = query.read()
			if "Wikipedia does not have a" in data:
				return False
			return True
		def get_submitter(name="", talk=False):
			enname = re.sub(" ", "_", name)
			if talk == True:
				enname = "Wikipedia_talk:Articles_for_creation/%s" % enname
			if talk == False:
				enname = "Wikipedia:Articles_for_creation/%s" % enname
			url = "http://en.wikipedia.org/w/api.php?action=query&titles=%s&prop=revisions&rvprop=user&rvdir=newer&rvlimit=1" % enname
			query = urllib.urlopen(url)
			data = query.read()
			extract = re.findall("user=&quot;(.*?)&quot;", data)
			if "anon=" in data:
				anon = True
			else:
				anon = False
			try:
				return extract[0], anon
			except BaseException:
				print extract
				return "", anon
		try:
			rawSub = line2[4]
			rawSub = ' '.join(line2[4:])
		except Exception:
			reply("You need to specify a submission name in order to use %s!" % command, chan, nick)
			return
		talk = False
		if "[[" in rawSub and "]]" in rawSub:
			name = re.sub("\[\[(.*)\]\]", "\\1", rawSub)
			name = re.sub(" ", "_", name)
			name = urllib.quote(name, ":/")
			name = "http://en.wikipedia.org/wiki/%s" % name
			if "talk:" in name:
				talk = True
		elif "http://" in rawSub:
			name = rawSub
			if "talk:" in name:
				talk = True
		elif "en.wikipedia.org" in rawSub:
			name = "http://%s" % rawSub
			if "talk:" in name:
				talk = True
		elif "Wikipedia:" in rawSub or "Wikipedia_talk:" in rawSub or "Wikipedia talk:" in rawSub:
			name = re.sub(" ", "_", rawSub)
			name = urllib.quote(name, ":/")
			name = "http://en.wikipedia.org/wiki/%s" % name
			if "talk:" in name:
				talk = True
		else:
			url = "http://en.wikipedia.org/wiki/"
			pagename = re.sub(" ", "_", rawSub)
			pagename = urllib.quote(pagename, ":/")
			pagename = "Wikipedia:Articles_for_creation/%s" % pagename
			page = urllib.urlopen("%s%s" % (url, pagename))
			text = page.read()
			name = "http://en.wikipedia.org/wiki/%s" % pagename
			if "Wikipedia does not have a" in text:
				pagename = re.sub(" ", "_", rawSub)
				pagename = urllib.quote(pagename, ":/")
				pagename = "Wikipedia_talk:Articles_for_creation/%s" % pagename
				page = urllib.urlopen("%s%s" % (url, pagename))
				name = "http://en.wikipedia.org/wiki/%s" % pagename
				talk = True
		unname = re.sub("http://en.wikipedia.org/wiki/Wikipedia:Articles_for_creation/", "", name)
		unname = re.sub("http://en.wikipedia.org/wiki/Wikipedia_talk:Articles_for_creation/", "", unname)
		unname = re.sub("_", " ", unname)
		if "talk" in unname:
			talk = True
		submitter, anon = get_submitter(name=unname, talk=talk)
		status = find_status(name=unname, talk=talk)
		if submitter != "":
			if anon == True:
				submitter_page = "Special:Contributions/%s" % submitter
			if anon == False:
				unsubmit = re.sub(" ", "_", submitter)
				unsubmit = urllib.quote(unsubmit, ":/")
				submitter_page = "User:%s" % unsubmit
			if status == "Accepted":
				submitterm = "Reviewer"
			else:
				submitterm = "Submitter"
		line1 = "\x02AfC submission report for %s:" % unname
		line2 = "\x02URL: \x0301\x0F%s" % name
		if submitter != "":
			line3 = "\x02%s: \x0F\x0302%s (\x0301\x0Fhttp://en.wikipedia.org/wiki/%s)." % (submitterm, submitter, submitter_page)
		line4 = "\x02Status: \x0F\x0302%s." % status
		say(line1, chan)
		time.sleep(0.1)
		say(line2, chan)
		time.sleep(0.1)
		if submitter != "":
			say(line3, chan)
			time.sleep(0.1)
		say(line4, chan)
		return
	if command == "commands":
		if chan.startswith("#"):
			reply("Please use that command in a private message.", chan, nick)
			return
		others2 = get_commandList().values()
		others = []
		for com in others2:
			if com == "copyvio" or com == "number" or com == "pending" or com == "report" or com == "submissions" or com == "access" or com == "help" or com == "join" or com == "linker" or com == "nick" or com == "op" or com == "part" or com == "quiet" or com == "quit" or com == "restart" or com == "voice" or com == "welcome" or com == "fish" or com == "praise" or com == "trout" or com == "notes":
				continue
			if com in others: continue
			others.append(com)
		others.sort()
		say("\x02AFC commands:\x0F copyvio, number, pending, report, submissions.", chan)
		time.sleep(0.1)
		say("\x02Bot operation and channel maintaince commands:\x0F access, help, join, linker, nick, op, part, quiet, quit, restart, voice, welcome.", chan)
		time.sleep(0.1)
		say("\x02Fun commands:\x0F fish, praise, trout, and numerous easter eggs", chan)
		time.sleep(0.1)
		say("\x02Other commands:\x0F %s" % ', '.join(others), chan)
		time.sleep(0.1)
		say("The bot maintains a mini-wiki. Type \"!notes help\" for more information.", chan)
		time.sleep(0.1)
		say("See http://enwp.org/User:The_Earwig/Bots/IRC for details. For help on a specific command, type '!help command'.", chan)
		return
	if command == "help" or command == "doc" or command == "documentation":
		try:
			com = line2[4]
		except Exception:
			reply("Hi, I'm a bot that does work for Articles for Creation. You can find information about me at http://enwp.org/User:The_Earwig/Bots/IRC. Say \"!commands\" to me in a private message for some of my abilities. Earwig is my owner and creator, and you can contact him at http://enwp.org/User_talk:The_Earwig.", chan, nick)
			return
		say("Sorry, command documentation has not been implemented yet.", chan)
		return
	if command == "mysql":
		if authy != "owner":
			reply("You aren't authorized to use this command.", chan, nick)
			return
		import MySQLdb
		try:
			strings = line2[4]
			strings = ' '.join(line2[4:])
			if "db:" in strings:
				database = re.findall("db\:(.*?)\s", strings)[0]
			else:
				database = "enwiki_p"
			if "time:" in strings:
				times = int(re.findall("time\:(.*?)\s", strings)[0])
			else:
				times = 60
			file = re.findall("file\:(.*?)\s", strings)[0]
			sqlquery = re.findall("query\:(.*?)\Z", strings)[0]
		except Exception:
			reply("You did not specify enough data for the bot to continue.", chan, nick)
			return
		database2 = database[:-2] + "-p"
		db = MySQLdb.connect(db=database, host="%s.rrdb.toolserver.org" % database2, read_default_file="/home/earwig/.my.cnf")
		db.query(sqlquery)
		r = db.use_result()
		data = r.fetch_row(0)
		try:
			f = codecs.open("/home/earwig/public_html/reports/%s/%s" % (database[:-2], file), 'r')
			reply("A file already exists with that name.", chan, nick)
			return
		except Exception:
			pass
		f = codecs.open("/home/earwig/public_html/reports/%s/%s" % (database[:-2], file), 'a', 'utf-8')
		for line in data:
			new_line = []
			for l in line:
				new_line.append(str(l))
			f.write('	'.join(new_line) + "\n")
		f.close()
		reply("Query completed successfully. See http://toolserver.org/~earwig/reports/%s/%s. I will delete the report in %s seconds." % (database[:-2], file, times), chan, nick)
		time.sleep(times)
		os.remove("/home/earwig/public_html/reports/%s/%s" % (database[:-2], file))
		return
	if command == "remind" or command == "reminder":
		try:
			times = int(line2[4])
			content = ' '.join(line2[5:])
		except Exception:
			reply("Please specify a time and a note in the following format: !remind <time> <note>.", chan, nick)
			return
		reply("Set reminder for \"%s\" in %s seconds." % (content, times), chan, nick)
		time.sleep(times)
		reply(content, chan, nick)
		return
	if command == "notes" or command == "note" or command == "about" or command == "data" or command == "database":
		try:
			action = line2[4]
		except BaseException:
			reply("What do you want me to do? Type \"!notes help\" for more information.", chan, nick)
			return
		import MySQLdb
		db = MySQLdb.connect(db="u_earwig_ircbot", host="sql", read_default_file="/home/earwig/.my.cnf")
		specify = ' '.join(line2[5:])
		if action == "help" or action == "manual":
			shortCommandList = "read, write, change, undo, delete, move, author, category, list, report, developer"
			if specify == "read":
				say("To read an entry, type \"!notes read <entry>\".", chan)
			elif specify == "write":
				say("To write a new entry, type \"!notes write <entry> <content>\". This will create a new entry only if one does not exist, see the below command...", chan)
			elif specify == "change":
				say("To change an entry, type \"!notes change <entry> <new content>\". The old entry will be stored in the database, so it can be undone later.", chan)
			elif specify == "undo":
				say("To undo a change, type \"!notes undo <entry>\".", chan)
			elif specify == "delete":
				say("To delete an entry, type \"!notes delete <entry>\". For security reasons, only bot admins can do this.", chan)
			elif specify == "move":
				say("To move an entry, type \"!notes move <old_title> <new_title>\".", chan)
			elif specify == "author":
				say("To return the author of an entry, type \"!notes author <entry>\".", chan)
			elif specify == "category" or specify == "cat":
				say("To change an entry's category, type \"!notes category <entry> <category>\".", chan)
			elif specify == "list":
				say("To list all categories in the database, type \"!notes list\". Type \"!notes list <category>\" to get all entries in a certain category.", chan)
			elif specify == "report":
				say("To give some statistics about the mini-wiki, including some debugging information, type \"!notes report\" in a PM.", chan)
			elif specify == "developer":
				say("To do developer work, such as writing to the database directly, type \"!notes developer <command>\". This can only be done by the bot owner.", chan)
			else:
				db.query("SELECT * FROM version;")
				r = db.use_result()
				data = r.fetch_row(0)
				version = data[0]
				reply("The Earwig Mini-Wiki: running v%s." % version, chan, nick)
				reply("The full list of commands, for reference, are: %s." % shortCommandList, chan, nick)
				reply("For an explaination of a certain command, type \"!notes help <command>\".", chan, nick)
				reply("You can also access the database from the Toolserver: http://toolserver.org/~earwig/cgi-bin/irc_database.py", chan, nick)
				time.sleep(0.4)
			return
		elif action == "read":
			specify = string.lower(specify)
			if " " in specify: specify = string.split(specify, " ")[0]
			if not specify or "\"" in specify:
				reply("Please include the name of the entry you would like to read after the command, e.g. !notes read earwig", chan, nick)
				return
			try:
				db.query("SELECT entry_content FROM entries WHERE entry_title = \"%s\";" % specify)
				r = db.use_result()
				data = r.fetch_row(0)
				entry = data[0][0]
				say("Entry \"\x02%s\x0F\": %s" % (specify, entry), chan)
			except Exception:
				reply("There is no entry titled \"\x02%s\x0F\"." % specify, chan, nick)
			return
		elif action == "delete" or action == "remove":
			specify = string.lower(specify)
			if " " in specify: specify = string.split(specify, " ")[0]
			if not specify or "\"" in specify:
				reply("Please include the name of the entry you would like to delete after the command, e.g. !notes delete earwig", chan, nick)
				return
			if authy == "owner" or authy == "admin":
				try:
					db.query("DELETE from entries where entry_title = \"%s\";" % specify)
					r = db.use_result()
					db.commit()
					reply("The entry on \"\x02%s\x0F\" has been removed." % specify, chan, nick)
				except Exception:
					phenny.reply("Unable to remove the entry on \"\x02%s\x0F\", because it doesn't exist." % specify, chan, nick)
			else:
				reply("Only bot admins can remove entries.", chan, nick)
			return
		elif action == "developer":
			if authy == "owner":
				db.query(specify)
				r = db.use_result()
				try:
					print r.fetch_row(0)
				except Exception:
					pass
				db.commit()
				reply("Done.", chan, nick)
			else:
				reply("Only the bot owner can modify the raw database.", chan, nick)
			return
		elif action == "write":
			try:
				write = line2[5]
				content = ' '.join(line2[6:])
			except Exception:
				reply("Please include some content in your entry.", chan, nick)
				return
			db.query("SELECT * from entries WHERE entry_title = \"%s\";" % write)
			r = db.use_result()
			data = r.fetch_row(0)
			if data:
				reply("An entry on %s already exists; please use \"!notes change %s %s\"." % (write, write, content), chan, nick)
				return
			content2 = content.replace('"', '\\' + '"')
			db.query("INSERT INTO entries (entry_title, entry_author, entry_category, entry_content, entry_content_old) VALUES (\"%s\", \"%s\", \"uncategorized\", \"%s\", NULL);" % (write, nick, content2))
			db.commit()
			reply("You have written an entry titled \"\x02%s\x0F\", with the following content: \"%s\"" % (write, content), chan, nick)
			return
		elif action == "change":
			reply("NotImplementedError", chan, nick)
		elif action == "undo":
			reply("NotImplementedError", chan, nick)
		elif action == "move":
			reply("NotImplementedError", chan, nick)
		elif action == "author":
			try:
				entry = line2[5]
			except Exception:
				reply("Please include the name of the entry you would like to get information for after the command, e.g. !notes author earwig", chan, nick)
				return
			db.query("SELECT entry_author from entries WHERE entry_title = \"%s\";" % entry)
			r = db.use_result()
			data = r.fetch_row(0)
			if data:
				say("The author of \"\x02%s\x0F\" is \x02%s\x0F." % (entry, data[0][0]), chan)
				return
			reply("There is no entry titled \"\x02%s\x0F\"." % entry, chan, nick)
			return
		elif action == "cat" or action == "category":
			reply("NotImplementedError", chan, nick)
		elif action == "list":
			reply("NotImplementedError", chan, nick)
		elif action == "report":
			reply("NotImplementedError", chan, nick)
	if command == "hash":
		import hashlib
		try:
			hashVia = line2[4]
			hashText = line2[5]
			hashText = ' '.join(line2[5:])
		except Exception:
			reply("Please provide a string and method to hash by.", chan, nick)
			return
		try:
			hashed = eval("hashlib.%s(\"%s\").hexdigest()" % (hashVia, hashText))
			reply(hashed, chan, nick)
		except Exception:
			try:
				hashing = hashlib.new(hashVia)
				hashing.update(hashText)
				hashed = hashing.hexdigest()
				reply(hashed, chan, nick)
			except Exception:
				reply("Error.", chan, nick)
	if command == "langcode" or command == "lang" or command == "language":
		try:
			lang = line2[4]
		except Exception:
			reply("Please specify an ISO code.", chan, nick)
			return
		data = urllib.urlopen("http://toolserver.org/~earwig/cgi-bin/swmt.py?action=iso").read()
		data = string.split(data, "\n")
		result = False
		for datum in data:
			if datum.startswith(lang):
				result = re.findall(".*? (.*)", datum)[0]
				break
		if result:
			reply(result, chan, nick)
			return
		reply("Not found.", chan, nick)
		return
	if command == "lookup" or command == "ip":
		try:
			hexIP = line2[4]
		except Exception:
			reply("Please specify a hex IP address.", chan, nick)
			return
		hexes = [hexIP[:2], hexIP[2:4], hexIP[4:6], hexIP[6:8]]
		hashes = []
		for hexHash in hexes:
			newHex = int(hexHash, 16)
			hashes.append(newHex)
		normalizedIP = "%s.%s.%s.%s" % (hashes[0], hashes[1], hashes[2], hashes[3])
		reply(normalizedIP, chan, nick)
		return