# Copyright (c) 2012 Web Notes Technologies Pvt Ltd (http://erpnext.com)
# 
# MIT License (MIT)
# 
# Permission is hereby granted, free of charge, to any person obtaining a 
# copy of this software and associated documentation files (the "Software"), 
# to deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the 
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# 

from __future__ import unicode_literals
"""
globals attached to webnotes module
+ some utility functions that should probably be moved
"""

code_fields_dict = {
	'Page':[('script', 'js'), ('content', 'html'), ('style', 'css'), ('static_content', 'html'), ('server_code', 'py')],
	'DocType':[('server_code_core', 'py'), ('client_script_core', 'js')],
	'Search Criteria':[('report_script', 'js'), ('server_script', 'py'), ('custom_query', 'sql')],
	'Patch':[('patch_code', 'py')],
	'Stylesheet':['stylesheet', 'css'],
	'Page Template':['template', 'html'],
	'Control Panel':[('startup_code', 'js'), ('startup_css', 'css')]
}

class _dict(dict):
	"""dict like object that exposes keys as attributes"""
	def __getattr__(self, key):
		return self.get(key)
	def __setattr__(self, key, value):
		self[key] = value
	def __getstate__(self): 
		return self
	def __setstate__(self, d): 
		self.update(d)
	def update(self, d):
		"""update and return self -- the missing dict feature in python"""
		super(_dict, self).update(d)
		return self
	def copy(self):
		return _dict(super(_dict, self).copy())
		
def _(msg):
	"""translate object in current lang, if exists"""
	from webnotes.translate import messages
	return messages.get(lang, {}).get(msg, msg)

request = form_dict = _dict()
conn = None
_memc = None
form = None
session = None
user = None
incoming_cookies = {}
add_cookies = {} # append these to outgoing request
cookies = {}
response = _dict({'message':'', 'exc':''})
error_log = []
debug_log = []
message_log = []
mute_emails = False
test_objects = {}
request_method = None
print_messages = False
user_lang = False
lang = 'en'

# memcache

def cache():
	global _memc
	if not _memc:
		from webnotes.memc import MClient
		_memc = MClient(['localhost:11211'])
	return _memc
		
class DuplicateEntryError(Exception): pass
class ValidationError(Exception): pass
class AuthenticationError(Exception): pass
class PermissionError(Exception): pass
class OutgoingEmailError(ValidationError): pass
class UnknownDomainError(Exception): pass
class SessionStopped(Exception): pass
class MappingMismatchError(ValidationError): pass
class InvalidStatusError(ValidationError): pass
class DoesNotExistError(ValidationError): pass
		
def getTraceback():
	import utils
	return utils.getTraceback()

def errprint(msg):
	if not request_method:
		print repr(msg)

	from utils import cstr
	error_log.append(cstr(msg))

def log(msg):
	if not request_method:
		import conf
		if getattr(conf, "logging", False):
			print repr(msg)
	
	from utils import cstr
	debug_log.append(cstr(msg))

def msgprint(msg, small=0, raise_exception=0, as_table=False):
	from utils import cstr
	if as_table and type(msg) in (list, tuple):
		msg = '<table border="1px" style="border-collapse: collapse" cellpadding="2px">' + ''.join(['<tr>'+''.join(['<td>%s</td>' % c for c in r])+'</tr>' for r in msg]) + '</table>'
	
	if print_messages:
		print "Message: " + repr(msg)
	
	message_log.append((small and '__small:' or '')+cstr(msg or ''))
	if raise_exception:
		import inspect
		if inspect.isclass(raise_exception) and issubclass(raise_exception, Exception):
			raise raise_exception, msg
		else:
			raise ValidationError, msg
	
def create_folder(path):
	import os
	try:
		os.makedirs(path)
	except OSError, e:
		if e.args[0]!=17: 
			raise e

def create_symlink(source_path, link_path):
	import os
	try:
		os.symlink(source_path, link_path)
	except OSError, e:
		if e.args[0]!=17: 
			raise e

def remove_file(path):
	import os
	try:
		os.remove(path)
	except OSError, e:
		if e.args[0]!=2: 
			raise e
			
def connect(db_name=None, password=None):
	import webnotes.db
	global conn
	conn = webnotes.db.Database(user=db_name, password=password)
	
	global session
	session = _dict({'user':'Administrator'})
	
	import webnotes.profile
	global user
	user = webnotes.profile.Profile('Administrator')

def get_env_vars(env_var):
	import os
	return os.environ.get(env_var,'None')

remote_ip = get_env_vars('REMOTE_ADDR')		#Required for login from python shell
logger = None
	
def get_db_password(db_name):
	"""get db password from conf"""
	import conf
	
	if hasattr(conf, 'get_db_password'):
		return conf.get_db_password(db_name)
		
	elif hasattr(conf, 'db_password'):
		return conf.db_password
		
	else:
		return db_name

whitelisted = []
guest_methods = []
def whitelist(allow_guest=False, allow_roles=None):
	"""
	decorator for whitelisting a function
	
	Note: if the function is allowed to be accessed by a guest user,
	it must explicitly be marked as allow_guest=True
	
	for specific roles, set allow_roles = ['Administrator'] etc.
	"""
	def innerfn(fn):
		global whitelisted, guest_methods
		whitelisted.append(fn)

		if allow_guest:
			guest_methods.append(fn)

		if allow_roles:
			roles = get_roles()
			allowed = False
			for role in allow_roles:
				if role in roles:
					allowed = True
					break
			
			if not allowed:
				raise PermissionError, "Method not allowed"

		return fn
	
	return innerfn
	
def clear_cache(user=None, doctype=None):
	"""clear cache"""
	if doctype:
		from webnotes.model.doctype import clear_cache
		clear_cache(doctype)
	elif user:
		from webnotes.sessions import clear_cache
		clear_cache(user)
	else:
		from webnotes.sessions import clear_cache
		clear_cache()
	
def get_roles(user=None, with_standard=True):
	"""get roles of current user"""
	if not user:
		user = session.user

	if user=='Guest':
		return ['Guest']
		
	roles = [r[0] for r in conn.sql("""select role from tabUserRole 
		where parent=%s and role!='All'""", user)] + ['All']
		
	# filter standard if required
	if not with_standard:
		roles = filter(lambda x: x not in ['All', 'Guest', 'Administrator'], roles)
		
	return roles

def has_permission(doctype, ptype="read", doc=None):
	"""check if user has permission"""
	from webnotes.defaults import get_user_default_as_list
	if session.user=="Administrator": 
		return True
	if conn.get_value("DocType", doctype, "istable"):
		return True
	perms = conn.sql("""select `name`, `match` from tabDocPerm p
		where p.parent = %s
		and ifnull(p.`%s`,0) = 1
		and ifnull(p.permlevel,0) = 0
		and (p.role="All" or p.role in (select `role` from tabUserRole where `parent`=%s))
		""" % ("%s", ptype, "%s"), (doctype, session.user), as_dict=1)
	
	if doc:
		match_failed = {}
		for p in perms:
			if p.match:
				if ":" in p.match:
					keys = p.match.split(":")
				else:
					keys = [p.match, p.match]
					
				if doc.fields.get(keys[0],"[No Value]") \
						in get_user_default_as_list(keys[1]):
					return True
				else:
					match_failed[keys[0]] = doc.fields.get(keys[0],"[No Value]")
			else:
				# found a permission without a match
				return True

		# no valid permission found
		if match_failed:
			doctypelist = get_doctype(doctype)
			msg = _("Not allowed for: ")
			for key in match_failed:
				msg += "\n" + (doctypelist.get_field(key) and doctypelist.get_label(key) or key) \
					+ " = " + (match_failed[key] or "None")
			msgprint(msg)
		return False
	else:
		return perms and True or False

def generate_hash():
	"""Generates random hash for session id"""
	import hashlib, time
	return hashlib.sha224(str(time.time())).hexdigest()

def get_obj(dt = None, dn = None, doc=None, doclist=[], with_children = True):
	from webnotes.model.code import get_obj
	return get_obj(dt, dn, doc, doclist, with_children)

def doc(doctype=None, name=None, fielddata=None):
	from webnotes.model.doc import Document
	return Document(doctype, name, fielddata)

def doclist(lst=None):
	from webnotes.model.doclist import DocList
	return DocList(lst)

def bean(doctype=None, name=None, copy=None):
	from webnotes.model.bean import Bean
	if copy:
		return Bean(copy_doclist(copy))
	else:
		return Bean(doctype, name)

def get_doclist(doctype, name=None):
	return bean(doctype, name).doclist
	
def get_doctype(doctype, processed=False):
	import webnotes.model.doctype
	return webnotes.model.doctype.get(doctype, processed)

def delete_doc(doctype=None, name=None, doclist = None, force=0, ignore_doctypes=[], for_reload=False):
	import webnotes.model.utils
	webnotes.model.utils.delete_doc(doctype, name, doclist, force, ignore_doctypes, for_reload)

def clear_perms(doctype):
	conn.sql("""delete from tabDocPerm where parent=%s""", doctype)

def reset_perms(doctype):
	clear_perms(doctype)
	reload_doc(conn.get_value("DocType", doctype, "module"), "DocType", doctype)

def reload_doc(module, dt=None, dn=None):
	import webnotes.modules
	return webnotes.modules.reload_doc(module, dt, dn)

def rename_doc(doctype, old, new, debug=0, force=False, merge=False):
	from webnotes.model.rename_doc import rename_doc
	rename_doc(doctype, old, new, force=force, merge=merge)

def insert(doclist):
	import webnotes.model
	return webnotes.model.insert(doclist)

def get_method(method_string):
	modulename = '.'.join(method_string.split('.')[:-1])
	methodname = method_string.split('.')[-1]

	__import__(modulename)
	import sys
	moduleobj = sys.modules[modulename]
	return getattr(moduleobj, methodname)
	
def make_property_setter(args):
	args = _dict(args)
	bean([{
		'doctype': "Property Setter",
		'doctype_or_field': args.doctype_or_field or "DocField",
		'doc_type': args.doctype,
		'field_name': args.fieldname,
		'property': args.property,
		'value': args.value,
		'property_type': args.property_type or "Data",
		'__islocal': 1
	}]).save()

def get_application_home_page(user='Guest'):
	"""get home page for user"""
	hpl = conn.sql("""select home_page 
		from `tabDefault Home Page`
		where parent='Control Panel' 
		and role in ('%s') order by idx asc limit 1""" % "', '".join(get_roles(user)))
	if hpl:
		return hpl[0][0]
	else:
		from startup import application_home_page
		return application_home_page

def copy_doclist(in_doclist):
	new_doclist = []
	for d in in_doclist:
		if isinstance(d, dict):
			new_doclist.append(d.copy())
		else:
			new_doclist.append(doc(d.fields.copy()))

	return doclist(new_doclist)
	
def map_doclist(from_to_list, from_docname, to_doclist=None):
	from_doctype, to_doctype = from_to_list[0][0], from_to_list[0][1]
	if to_doclist:
		to_doclist = bean(to_doclist).doclist
	else:
		to_doclist = bean({"doctype": to_doctype}).doclist
	
	mapper = get_obj("DocType Mapper", "-".join(from_to_list[0]))
	to_doclist = mapper.dt_map(from_doctype, to_doctype, from_docname, to_doclist[0], to_doclist, from_to_list)
	return to_doclist

def compare(val1, condition, val2):
	import webnotes.utils
	return webnotes.utils.compare(val1, condition, val2)
	
def repsond_as_web_page(title, html):
	global message, message_title, response
	message_title = title
	message = "<h3>" + title + "</h3>" + html
	response['type'] = 'page'
	response['page_name'] = 'message.html'

_config = None
def get_config():
	global _config
	if not _config:
		import webnotes.utils, json
	
		_config = _dict({"modules": {}, "web": _dict({"pages": {}, "generators": {}})})
		with open(webnotes.utils.get_path("lib", "config.json"), "r") as configf:
			framework_config = json.loads(configf.read())
			_config.modules.update(framework_config["modules"])
			_config.web.pages.update(framework_config["web"]["pages"])
			_config.web.generators.update(framework_config["web"]["generators"])
		
		with open(webnotes.utils.get_path("app", "config.json"), "r") as configf:
			app_config = json.loads(configf.read())
			_config.modules.update(app_config["modules"])
			_config.web.pages.update(app_config["web"]["pages"])
			_config.web.generators.update(app_config["web"]["generators"])
		
	return _config
		