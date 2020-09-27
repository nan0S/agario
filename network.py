import socket
import _pickle as pickle

class Network:
	
	BUFFER = 16 * 2048

	def __init__(self):
		self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.port = 6666

		# use this to run the game on local server (every player on the same computer)
		# self.host = '127.0.1.1'
		self.host = socket.gethostbyname(socket.gethostname())

		# use this to run the game on your network (every player on the same network) 
		# you have to change this IP to your network's IP (also has to be done in server.py)
		# self.host = '192.168.1.134'


	def connect(self, name):
		self.conn.connect((self.host, self.port))
		print('[INFO] Connected to the server!')
		self.id = self.send(name)


	def disconnect(self):
		self.conn.close()


	def send(self, data):
		self.conn.send(pickle.dumps(data))
		return pickle.loads(self.conn.recv(Network.BUFFER))


	def receive(self, count):
		return pickle.loads(self.conn.recv(count))