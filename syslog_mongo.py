#!/usr/bin/python

# Syslog to Mongo bridge

import SocketServer
import time
import json
import pymongo
import new
import re

from pymongo import MongoClient

CONFIG_FILE = 'config.json'
config = {}

def load_config(delay=0):
	global config
	now = time.time()

	if (delay == 0) or (now - config['updated'] > delay):
		print "Loading config file."
		f = open(CONFIG_FILE, 'r')
		config = json.loads(f.read())
		config['updated'] = now
		print config
		
load_config()

def import_code(code, name, add_to_sys_modules=False):
	name = name.encode('ascii')
	module = new.module(name)
	if add_to_sys_modules:
		import sys
		sys.modules[name] = module
	exec code in module.__dict__
	return module

client = MongoClient(config['mongo_host'], config['mongo_port'])

class SyslogUDPHandler(SocketServer.BaseRequestHandler):
		
	
	def generate_output(self, data):
		output = {}
		# need code for multi match here
		for filter in config['filters']:
			match = re.search(filter['regex'], data)
			if match:
				# This should probably be cached eventually
				script = import_code(open(filter['script']),filter['id'])
				output['data'] = script.process(match,data)
				output['filter'] = filter
		return output

	def handle(self):
		load_config(config['delay'])
		
		data = bytes.decode(self.request[0].strip())
		
		output = self.generate_output(data)
		print output
		db = client.test
		logs = db.logs
		log_id = logs.insert(output)
		print "Added log to db : {0}".format(log_id)


if __name__ == "__main__":
	try:
		print "Starting up server @ {0}:{1}".format(config['bind_host'], config['port'])
		server = SocketServer.UDPServer((config['bind_host'], config['port']), SyslogUDPHandler)
		server.serve_forever()
	except (IOError, SystemExit):
		raise
	except KeyboardInterrupt:
		print ("Shutting down.")
