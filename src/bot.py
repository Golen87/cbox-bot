import re, pprint

from utils import bold, italic, underline, strike, quote
from cbox import Cbox
import config


#--- Cbox Setup ---#

cbox = Cbox(config.myBoxInfo, config.myBotInfo, config.myLoginInfo)


#--- Bot methods ---#

@cbox.method("!hello")
def greetUser(message):
	return "Hi %s!" % message.name

@cbox.method("!ping")
def ping(message):
	elapsed = time.time() - message.time
	return "Pong! (%.2f seconds)" % elapsed

@cbox.method("!alias (.*)")
def getAlias(message, name):
	user = cbox.db.findUserByName(name)
	if not user:
		if not name:
			return "Sorry, I don't recognize that."
		return "Sorry, I don't recognize the name %s." % (italic(name))

	aliases = cbox.db.getAlias(user.name)
	aliases = [(n, cbox.db.getPostCountByUser(n)) for n in aliases]
	aliases.sort(key=lambda x:x[1], reverse=True)
	aliases = [italic(a[0]) for a in aliases]

	if len(aliases) == 0:
		return "Sorry, I haven't seen %s by any other name." % (italic(user.name))

	limit = 4
	if len(aliases) > limit + 1:
		end = 'and %d other names' % (len(aliases[limit:]))
		aliases = aliases[:limit] + [end]

	return "%s is also known as: %s." % (user.name, ', '.join(aliases))


#--- Run bot ---#

cbox.run()
