# -*- coding: utf-8  -*-
######
###### NOTE:
###### This is an old commands file from the previous version of EarwigBot.
###### It is not used by the new EarwigBot and is simply here for reference
###### when developing new commands.
######
### EarwigBot

def parse(command, line, line2, nick, chan, host, auth, notice, say, reply, s):
	authy = auth(host)
	if command == "access":
		a = 'The bot\'s owner is "%s".' % OWNER
		b = 'The bot\'s admins are "%s".' % ', '.join(ADMINS_R)
		reply(a, chan, nick)
		reply(b, chan, nick)
		return
	if command == "tock":
		u = urllib.urlopen('http://tycho.usno.navy.mil/cgi-bin/timer.pl')
		info = u.info()
		u.close()
		say('"' + info['Date'] + '" - tycho.usno.navy.mil', chan)
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
