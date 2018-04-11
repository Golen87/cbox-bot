# -*- coding: utf-8 -*-
# Copyright (c) 2018, Måns Gezelius (Golen)
# All rights reserved.

import re, pycurl, io, json, traceback, time
import twill.commands as twill
from bs4 import BeautifulSoup
from urllib import urlencode

from database import Database
import utils


# CBox handles all communication with cbox.ws, reading and sending messages.
class Cbox:
	def __init__(self, boxInfo, botInfo, loginInfo):
		self.boxInfo = boxInfo
		self.botInfo = botInfo
		self.loginInfo = loginInfo

		self.db = None
		
		self.lastChatId = None

		self.userMethods = []

		self.lastChatTime = time.time()
		self.lastCommandTime = time.time()
		self.lastFetchTime = 0
		self.lastFetchMsgCount = 0


	# Parse html
	def _toHtml(self, data):
		return BeautifulSoup(data, "html.parser")

	# Returns the max number of pages to check
	def _findMaxPage(self, html):
		pageStr = html.find(align="right").text
		digit = pageStr.strip().split()[-1]
		if '[' in digit or '-' in digit:
			return 1
		return int(digit)

	# Return data from all available pages of a given url (posts, users, bans)
	def _requestPages(self, url, page=1, expired=False):
		twill.go("{}?pg={}".format(url, page))
		#twill.go(url.replace(".html", "_{}.html".format(page)))
		response = twill.browser.get_html()

		if "Your session has expired." in response:
			if expired:
				raise Exception("Unable to log into cbox! Your session has expired.")
			self.login()
			return self._requestPages(url, page, True)

		if page == 1:
			html = self._toHtml(response)
			maxPage = self._findMaxPage(html)
			return [html] + [self._requestPages(url, page+i, expired) for i in range(1,maxPage)]

		return self._toHtml(response)


	#-- Cbox control panel lists --#

	def login(self):
		print "Logging in..."
		twill.go("https://www.cbox.ws")

		twill.formclear("1")
		twill.fv("1", "uname", self.loginInfo["username"])
		twill.fv("1", "pword", self.loginInfo["password"])

		twill.submit("0")

		response = twill.browser.get_html()
		if "Incorrect username or password." in response:
			raise Exception("Unable to log into cbox! Incorrect username or password.")

	# Return list of users from cbox control panel
	def fetchUsers(self):
		print "Getting users..."
		pages = self._requestPages("https://www.cbox.ws/admin_l_users")
		#pages = self._requestPages("https://www.golen.nu/portal/Cbox_Registered_Users.html")

		users = []

		for html in pages:
			trs = html.findAll("tr")
			for tri in range(1, len(trs)):
				tds = trs[tri].findAll("td")
				nameData = tds[1].contents

				user = {}

				user["name"] = nameData.pop().strip()
				user["roles"] = [n.text[1:-1] for n in nameData[::2]]
				user["token"] = tds[2].text
				user["registered"] = tds[3].text.strip()
				user["last used"] = tds[4].text.strip()
				user["ip"] = tds[5].text.strip()

				users.append(user)

		return users

	# Return list of messages from cbox control panel
	def fetchPosts(self):
		print "Getting posts..."
		pages = self._requestPages("https://www.cbox.ws/admin_l_posts")
		#pages = self._requestPages("https://www.golen.nu/portal/Cbox_Posts.html")

		posts = []

		for html in pages:
			trs = html.findAll("tr")
			for tri in range(1, len(trs)):
				tds = trs[tri].findAll("td")
				msgData = tds[1].contents
				dateData = tds[2].text.splitlines()

				post = {}

				post["name"] = msgData[0].text
				post["email"] = msgData[1].strip()
				post["content"] = msgData[2].text
				post["date"] = dateData[0]
				post["ip"] = dateData[1]

				posts.append(post)

		return posts

	# Return list of bans from cbox control panel
	def fetchBans(self):
		print "Getting bans..."
		pages = self._requestPages("https://www.cbox.ws/admin_l_bans")

		bans = []

		for html in pages:
			trs = html.findAll("tr")
			for tri in range(1, len(trs)):
				tds = trs[tri].findAll("td")
				if "No bans found" in tds[0].text:
					break

				ban = {}

				ban["name"] = tds[1].text.strip() # ???
				ban["reason"] = tds[2].text.strip()
				ban["ip"] = tds[3].text.strip()
				ban["date"] = tds[4].text.strip()
				ban["expiry"] = tds[5].text.strip()

				bans.append(ban)

		return bans


	#-- Message handling --#

	# Starts from last message in history and searches forward to the most recent id.
	# The latest id ensures we only collect new/unread messages.
	def findLatestChatId(self):
		print "Finding most recent message id..."

		# Since cbox's history is limited, the server returns
		# the oldest available message when msgId=0 is requested.
		msgId = 0
		lastId = 0

		# If cbox is Pro with larger history, this function oughta be optimized.
		while True:
			messages = self.getChat(msgId)
			if len(messages) == 0:
				print "Message id found ({})".format(msgId)
				return msgId
			msgId = messages[0].id

			if msgId <= lastId:
				raise Exception("Something went wrong.")
			lastId = msgId

	# Fetch chat messages from the cbox chat
	# Returns list of CboxMessage objects from msgId and forward.
	def getChat(self, msgId=None):
		# If no message id is specified, pick the most recent chat id.
		if msgId == None:
			if self.lastChatId == None:
				self.lastChatId = self.findLatestChatId()
			msgId = self.lastChatId

		get = {
			'i': msgId, # Message id
			'k': self.botInfo['token'], # Bot token
			'fwd': 1, # ?
			'aj': 1 # Cbox version
		}
		url = "www{}.cbox.ws/box/?boxid={}&boxtag={}&sec=archive".format(self.boxInfo['srv'], self.boxInfo['id'], self.boxInfo['tag'])
		url += "&" + urlencode(get)

		try:
			# Send GET request to url, writing response to buf
			buf = io.BytesIO()

			c = pycurl.Curl()
			c.setopt(c.WRITEFUNCTION, buf.write)
			c.setopt(c.URL, url)
			c.perform()

			code = c.getinfo(pycurl.HTTP_CODE)
			if code < 200 or code >= 300:
				raise Warning("Cannot connect to cbox. Please check that boxInfo is correct.")

			result = buf.getvalue().decode('utf-8')
			result = result.split('\n')[1:]

		except pycurl.error:
			print 'WARNING: Cannot connect to cbox'
			return []
		finally:
			buf.close()

		# Return list of CboxMessage objects
		messages = []

		try:
			posts = [line.split('\t') for line in result]

			for data in posts:
				message = CboxMessage(data)
				messages.append(message)

				if self.lastChatId != None:
					if message.id > self.lastChatId:
						self.lastChatId = message.id

		except Exception as e:
			traceback.print_exc()
			print
		finally:
			return messages

	# Send chat message to the cbox chat
	def postChat(self, msg):
		print ">", msg

		post = {
			'nme': self.botInfo['name'], # Username
			'key': self.botInfo['token'], # Bot token
			'eml': self.botInfo['url'], # Image url
			'pst': msg.encode('utf-8'), # Message
			'aj': '1' # Cbox version
		}
		url = "www{}.cbox.ws/box/?boxid={}&boxtag={}&sec=submit".format(self.boxInfo['srv'], self.boxInfo['id'], self.boxInfo['tag'])

		try:
			# Send POST request to url, writing response to buf
			buf = io.BytesIO()

			c = pycurl.Curl()
			c.setopt(c.URL, url)
			c.setopt(c.WRITEFUNCTION, buf.write)
			c.setopt(c.POSTFIELDS, urlencode(post))
			c.perform()

			code = c.getinfo(pycurl.HTTP_CODE)
			if code < 200 or code >= 300:
				raise Warning("Cannot connect to cbox. Please check that boxInfo is correct.")

			result = buf.getvalue().decode('utf-8')
			result = result[1:-1].split('\t')

		except pycurl.error:
			print 'WARNING: Cannot connect to cbox'
			return []
		finally:
			buf.close()

		# Unused
		errmsg = result[0]		
		unknown = result[1]
		time = int(result[2])
		token = result[3]
		unknown2 = result[4] #8
		msgId = int(result[5]) # Do not use to update lastChatId. May miss incoming messages.
		errcode = result[6]

		if unknown:
			print 'WARNING: Unknown value "unknown" = "%s"' % (unknown)
		if unknown2 != '8':
			print 'WARNING: Unknown value "unknown2" = "%s"' % (unknown2)

		if errcode:
			print 'ERROR:', errcode, errmsg
			return


	#--- User methods management ---#

	# Decorator that stores a method with a given regex
	def method(self, expr):
		regex = re.compile(expr, re.IGNORECASE)

		def wrapper(func):
			self.userMethods.append((regex, func))

			def func_wrapper(message, *args, **kwargs):
				return func(message, *args, **kwargs)
			return func_wrapper
		return wrapper


	#--- Main loop ---#

	# Handle one new message
	def _onMessage(self, message):
		self.lastFetchMsgCount += 1

		# Ignore messages older than 2 minutes (may occur if bot goes temporarily offline)
		if time.time() - message.time > 2*60:
			return

		# Ignore messages from self
		if message.name == self.botInfo['name']:
			return

		self.lastChatTime = message.time

		# Call user methods upon matching regex
		for regex, func in self.userMethods:
			match = regex.match(message.content)
			if match:
				print message
				self.lastCommandTime = message.time

				response = func(message, *match.groups())
				if response:
					self.postChat(str(response))

	# Gather new messages
	def fetchMessages(self):
		messages = self.getChat()
		messages.reverse()
		for message in messages:
			self._onMessage(message)

	# Update
	def fetchUpdates(self):
		print
		self.db.updateUsers(self.fetchUsers())
		self.fetchMessages() # Update fetching takes a while
		self.db.updatePosts(self.fetchPosts())
		#self.db.updateBans(self.fetchBans())

		self.lastFetchTime = time.time()
		self.lastFetchMsgCount = 0
		print 'Update complete'

	# Start the main loop.
	# It will continuously fetch messages and user info.
	def run(self):
		self.db = Database()

		# Main loop
		print
		print 'Starting main loop...'
		while True:
			self.fetchMessages()

			# Update at least every 200 messages
			if self.lastFetchMsgCount > 200:
				self.fetchUpdates()
			# Update at least once every 4 hours
			if time.time() - self.lastFetchTime > 4*60*60:
				self.fetchUpdates()

			# If no messages for 30 minutes, take it easy.
			if time.time() - self.lastChatTime > 30*60:
				time.sleep(15)
			# If no issued commands for 5 minutes, bot not needed.
			elif time.time() - self.lastCommandTime > 5*60:
				time.sleep(5)
			# People are using the bot.
			else:
				time.sleep(2)


# CboxMessage stores an incoming chat message from Cbox. These are not stored in the database.
class CboxMessage:
	levels = ["normal", "registered", "moderator", "admin", "bot", "reserved"]

	def __init__(self, data):
		self.id = int(data[0]) # Message id
		self.time = int(data[1]) # Unix timestamp
		self.date = utils.convertDate(data[2].split(',')[0]) # Date string
		self.name = data[3] # Author's name
		self.level = self.levels[int(data[4])-1] # Privileges
		self.exturl = data[5] # Email/url
		self.content = BeautifulSoup(data[6], "html.parser").text # Message text
		self.imgurl = data[7] # Image url
		self.badFlags = int(data[8]) # Message type flags
		self.userid = data[9] # Author's id
		self.flaghtml = data[10]
		self.localId = data[11]

		self.isRedirected = bool(self.badFlags & 16)
		self.isPrivate = bool(self.badFlags & 32)
		self.isSticky = self.id == -1
		self.isTemp = self.id == 0

	def __str__(self):
		return unicode(u'[{}] {}: {}'.format(self.date, self.name, self.content[:20])).encode('utf-8')
