import sys, os

from database import Database


if len(sys.argv) != 2:
	print 'python archiveReader.py <archive-file>'
	exit()

filename = sys.argv[1]

if not os.path.exists(filename) or os.path.getsize(filename) == 0:
	print 'python archiveReader.py <archive-file>'
	exit()


posts = []

with open(filename, 'r') as f:
	for line in f.read().decode('utf8').splitlines():
		data = line.split('\t')[1:]

		post = {}

		post['date'] = data[0]
		post['name'] = data[1]
		post['email'] = data[2]
		post['ip'] = data[3]
		post['content'] = data[4]

		posts.append(post)

db = Database()
db.updatePosts(posts)
