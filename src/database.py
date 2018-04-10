# -*- coding: utf-8 -*-
# Copyright (c) 2018, Måns Gezelius (Golen)
# All rights reserved.

import os, json, datetime
import utils
import config


# Database management class for userdata and posts.
class Database:
	dbPath = config.DB_PATH
	usersPath = config.DB_USERS_PATH
	postsPath = config.DB_POSTS_PATH

	def __init__(self):
		self.users = None
		self.posts = None

		self.load()


	# Load users and posts
	def load(self):
		self.loadUsers()
		self.loadPosts()

	# Load users database
	def loadUsers(self):
		self.users = {}

		if not os.path.exists(self.dbPath):
			os.makedirs(self.dbPath)

		filePath = self.dbPath + self.usersPath
		if os.path.exists(filePath) and os.path.getsize(filePath) > 0:
			with open(filePath, 'r') as file:
				package = json.loads(file.read())
				for pack in package:
					user = User()
					user.unpack(pack)
					self.users[user.name] = user
		print 'Loading database users... {} users loaded'.format(len(self.users))

	# Load posts database
	def loadPosts(self):
		self.posts = []

		if not os.path.exists(self.dbPath):
			os.makedirs(self.dbPath)

		filePath = self.dbPath + self.postsPath
		if os.path.exists(filePath) and os.path.getsize(filePath) > 0:
			with open(filePath, 'r') as file:
				package = file.read().decode('utf8').splitlines()
				for pack in package:
					post = Post()
					post.unpack(pack)
					self.posts.append(post)
		print 'Loading database posts... {} posts loaded'.format(len(self.posts))


	# Save users and posts
	def save(self):
		self.saveUsers()
		self.savePosts()

	# Save users database
	def saveUsers(self):
		if not os.path.exists(self.dbPath):
			os.makedirs(self.dbPath)

		filePath = self.dbPath + self.usersPath
		with open(filePath, 'w') as file:
			package = [self.users[user].pack() for user in self.users]
			package = json.dumps(package, ensure_ascii=False, indent=1)
			file.write(package.encode('utf-8'))

	# Save posts database
	def savePosts(self):
		if not os.path.exists(self.dbPath):
			os.makedirs(self.dbPath)

		filePath = self.dbPath + self.postsPath
		with open(filePath, 'w') as file:
			package = [post.pack()+'\n' for post in self.posts]
			package = [p.encode('utf8') for p in package]
			file.writelines(package)


	# Insert new userdata into users database
	def updateUsers(self, users):
		newUserCount = 0

		for data in users:
			user = User(data)
			if user.name in self.users:
				self.users[user.name].merge(user)
			else:
				self.users[user.name] = user
				newUserCount += 1

		if newUserCount > 0:
			print newUserCount, 'users inserted'
		self.saveUsers()

	# Insert new messages into posts database
	# [old, ..., new]
	def updatePosts(self, posts):
		if not posts:
			return
		if utils.convertDate(posts[0]['date']) > utils.convertDate(posts[-1]['date']):
			posts.reverse()
		for i in range(len(posts)-1):
			if utils.convertDate(posts[i]['date']) > utils.convertDate(posts[i+1]['date']):
				print 'ERROR: database.updatePosts incoming posts not in order'
				print '-', utils.convertDate(posts[i]['date']), utils.convertDate(posts[i+1]['date'])
				return

		newPostCount = 0
		newUserCount = 0

		dateLookup = {}

		for post in self.posts:
			if post.date in dateLookup:
				dateLookup[post.date].append(post)
			else:
				dateLookup[post.date] = [post]

		for data in posts:
			newPost = Post(data)
			isNew = True

			if newPost.date in dateLookup:
				if newPost in dateLookup[newPost.date]:
					isNew = False
				dateLookup[newPost.date].append(newPost)
			else:
				dateLookup[newPost.date] = [newPost]
			
			if isNew:
				if newPost.name not in self.users:
					user = User()
					user.name = newPost.name
					self.users[user.name] = user
					newUserCount += 1
				self.users[newPost.name].addIp(newPost.ip)

				self.posts.append(newPost)
				newPostCount += 1

		if newPostCount > 0:
			print newPostCount, 'posts inserted'
			self.posts.sort()
			self.savePosts()
		if newUserCount > 0:
			print newUserCount, 'users inserted'
			self.saveUsers()


	# Find all users related by name or ip
	def getAlias(self, name):
		if name not in self.users:
			return []

		checkedNames = []
		checkedIps = []

		def scanIp(ip):
			if ip not in checkedIps:
				checkedIps.append(ip)
				for name in self.users:
					user = self.users[name]
					if ip in user.ip:
						scanName(user.name)

		def scanName(name):
			if name not in checkedNames:
				checkedNames.append(name)
				for ip in self.users[name].ip:
					scanIp(ip)

		scanName(name)
		checkedNames.remove(name)
		return checkedNames

	# Get number of posts by a user
	def getPostCountByUser(self, name):
		count = 0
		for post in self.posts:
			if name == post.name:
				count += 1
		return count

	# Return username from fuzzy name search
	def findUserByName(self, name):
		if name in self.users:
			return self.users[name]
		for user in self.users:
			if name.lower() == user.lower():
				return self.users[user]
		return None


# User is used to store user information.
# A new User requires packed data from the database or extracted from Cbox control panel.
class User:
	def __init__(self, data=None):
		self.name = None
		self.roles = []
		self.ip = []
		self.lastUsed = None
		self.registered = None
		self.token = None

		if data:
			self.loadDict(data)

	def __str__(self):
		return unicode(u'<{}>'.format(self.name)).encode('utf-8')

	# Pack instance data to a dict
	def pack(self):
		return {
			'name': self.name,
			'roles': self.roles,
			'ip': self.ip,
			'last used': self.lastUsed,
			'registered': self.registered,
			'token': self.token
		}

	# Unpack dict data to instance
	def unpack(self, data):
		self.name = data['name']
		self.roles = data['roles']
		self.ip = data['ip']
		self.lastUsed = data['last used']
		self.registered = data['registered']
		self.token = data['token']

	# Load from admin users list
	def loadDict(self, data):
		self.name = data['name']
		for role in data['roles']:
			self.roles.append(role)
		if data['ip'] != '0.0.0.0':
			self.ip.append(data['ip'])
		self.lastUsed = utils.convertDate(data['last used'])
		self.registered = utils.convertDate(data['registered'])
		if data['token']:
			self.token = data['token']

	# Insert updated userdata
	def merge(self, user):
		self.roles = user.roles
		self.registered = user.registered
		self.token = user.token
		self.lastUsed = max(self.lastUsed, user.lastUsed)

		for ip in user.ip:
			self.addIp(ip)

	# Add ip to user
	def addIp(self, ip):
		if ip not in self.ip:
			self.ip.append(ip)


# Post is used to store one chat message.
# A new Post requires packed data from the database or extracted from Cbox control panel.
class Post:
	def __init__(self, data=None):
		self.date = None
		self.name = None
		self.content = None
		self.ip = None
		self.email = None #url

		if data:
			self.loadDict(data)

	def __str__(self):
		return unicode(u'<{}: {}>'.format(self.name, self.content[:20])).encode('utf-8')

	def __eq__(self, other):
		return self.date == other.date and self.name == other.name and self.content == other.content and self.ip == other.ip and self.email == other.email

	def __lt__(self, other):
		return self.date < other.date

	# Pack instance data to string
	def pack(self):
		data = [
			self.date,
			self.name,
			self.content,
			self.ip,
			self.email
		]
		return '\t'.join(data)

	# Unpack string to instance
	def unpack(self, data):
		data = data.split('\t')
		self.date = data[0]
		self.name = data[1]
		self.content = data[2]
		self.ip = data[3]
		self.email = data[4]

	# Load from admin posts list or archive
	def loadDict(self, data):
		self.date = utils.convertDate(data['date'])
		self.name = data['name']
		self.content = data['content']
		self.ip = data['ip']
		self.email = data['email']
