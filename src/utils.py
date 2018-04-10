import re

isDate = re.compile("^\d{4}-\d{2}-\d{2}.*$")

months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']


# Converts from "DD month YY [HH:MM:SS]" to "YYYY-MM-DD [HH:MM:SS]"
def convertDate(date):
	if date in [None, 'never']:
		return None
	if isDate.match(date):
		return date

	arr = date.split()
	if len(arr) == 4:
		d,m,y,t = arr
		return convertDate('%s %s %s' % (d, m, y)) + ' ' + t

	d,m,y = arr
	d,y = int(d), int(y)
	m = months.index(m) + 1
	return '20%02d-%02d-%02d' % (y, m, d)


# Return bold text
def bold(text):
	return "[b]%s[/b]" % (text)
	#return "**%s**" % (text)

# Return italicized text
def italic(text):
	return "[i]%s[/i]" % (text)
	#return "_%s_" % (text)

# Return underlined text
def underline(text):
	return "[u]%s[/u]" % (text)

# Return struck-out text
def strike(text):
	return "[s]%s[/s]" % (text)

# Return quoted text
def quote(text):
	return "[q]%s[/q]" % (text)

#[color=#ff0000]hex colour[/color] or [color=forestgreen]named colour[/color]
#[color=#f00,#ff0]foreground and background[/color]
#[sub]subscript[/sub]
#[sup]superscript[/sup]
#[center]centered text[/center]
#[br]
#(line break)
#[big]larger font[/big]
#[small]smaller font[/small]
#[class=custom]custom-styled text[/custom]
#[code]fixed-width text[/code]
#[url=http://address.com/hyperlink]link text[/url] or [url]http://address.com/hyperlink[/url]
#[img=http://address.com/image.jpg]image title[/img] or [img]http://address.com/image.jpg[/img]
