from database import Database

db = Database()


#--- Graph generation ---#

def printAliasGraph():
	unique = {}
	for name in db.users:
		new = True
		if name in unique:
			new = False
		for n in unique:
			if name in unique[n]:
				new = False

		if new:
			aliases = db.getAlias(name)
			unique[name] = aliases

	for name in unique:
		aliases = [name] + unique[name] + [name]
		aliases = ['"%s"' % (a) for a in aliases]
		if len(aliases) == 2:
			print aliases[0]
		else:
			print ' -> '.join(aliases)

def printIpGraph():
	ipToNames = {}
	for name in db.users:
		for ip in db.users[name].ip:
			asn = ip
			#asn = asnLookup.getAsn(ip)
			if asn not in ipToNames:
				ipToNames[asn] = []
			ipToNames[asn].append(name)
	
	namesToIps = {}
	for ip in ipToNames:
		key = '\\n'.join(ipToNames[ip])
		if key not in namesToIps:
			namesToIps[key] = []
		namesToIps[key].append(ip)
	
	allNames = [j for i in [n.split('\\n') for n in namesToIps.keys()] for j in i]
	uniqueNames = [name for name in db.users if allNames.count(name) == 1]

	for names in namesToIps:
		key = '\\n'.join(namesToIps[names][:2])
		if len(namesToIps[names]) > 2:
			key += '\\n%d more...' % (len(namesToIps[names]) - 2)
		unique = [n for n in names.split('\\n') if n in uniqueNames]
		for name in names.split('\\n'):
			if name not in unique:
				print '"%s" -> "%s"' % (name, key)
		if unique:
			print '"%s" -> "%s"' % ('\\n'.join(unique), key)
