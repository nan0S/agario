import socket
import _pickle as pickle
import time
from random import *
from math import sqrt, sin
from threading import Thread
from numpy import clip

class Player:

	def __init__(self, x, y, color, r, name, score):
		self.x = x
		self.y = y
		self.color = color
		self.r = r
		self.name = name
		self.score = score


	def update_pos(self, x, y):
		self.x = x
		self.y = y



class Server:

	HEADER = 10

	def __init__(self):
		self.serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.host_name = socket.gethostname()
		self.port = 6666
		# use this to run the server on local server (every player on the same computer)
		self.ip_addr = socket.gethostbyname(self.host_name)
		# use this IP if you want to play on your network (every player on the same network)
		# you have to change this IP to your network's IP (also has to be done in network.py)
		# self.ip_addr = '192.168.1.134'

	def start(self):
    	# initialize server
		try:
			self.serv.bind((self.ip_addr, self.port))

		except socket.error as e:
			print(e)
			print('[ERROR] Server could not start')
			quit()

		self.serv.listen()
		print(f'[SERVER] Server started with ip {self.ip_addr}!')

		# initialize game logic
		print('[SERVER] Setting up the game!')
		self.gameinit()

		# run the game
		print('[SERVER] Running the server!')
		self.run()


	def gameinit(self):
		self.client_id = 0
		self.width, self.height = 1280, 720
		self.scale = 5
		self.colors = [(255, 0, 0), (255, 127, 0), (255, 255, 0), (0, 255, 0), (0, 0, 255), (46, 43, 95), (139, 0, 255)]
		self.orb_radius = 10
		self.player_radius = 30
		self.orbs = []
		self.generate_orbs(randint(700, 700))
		self.players = {}


	def generate_orbs(self, count):
		for i in range(count):
			x, y = self.rand_location()
			color = self.pick_color()
			self.orbs.append((x, y, color))


	def rand_location(self):
		return (randint(0, self.width * self.scale), randint(0, self.height * self.scale))


	def pick_color(self):
		"""
		random color
		"""
		return choice(self.colors)


	def pick_location(self):
		"""
		random location that do not intersects with other player
		"""
		good = False
		while not good:
			good = True
			x, y = self.rand_location()
			for p in self.players.values():
				if self.collide(x, y, self.player_radius, p.x, p.y, p.r):
					good = False
					break
		return x, y


	def collide(self, x1, y1, r1, x2, y2, r2):
		return (x1 - x2) ** 2 + (y1 - y2) ** 2 <= (r1 + r2) ** 2


	def run(self):
		print('[SERVER] Waiting for connections!')

		try:
			while True:
    			# server waits for connection
				conn, addr = self.serv.accept()
				print(f'[CONNECTION] Connection from {addr} has been established!')
				# start client loop on the new thread
				Thread(target=self.handle_client, args=(conn,)).start()

		except KeyboardInterrupt:
			pass

		print('[SERVER] Shutting down the server!')
		self.serv.close()


	def send(self, conn, data):
		conn.send(pickle.dumps(data))


	def receive(self, conn):
		recv = conn.recv(40)
		if not recv:
			return False
		return pickle.loads(recv)


	def eat_orbs(self, p):
		for i, orb in enumerate(self.orbs):
			x, y = orb[0], orb[1]
			if self.collide(x, y, self.orb_radius, p.x, p.y, p.r * 0.9):
    			# if it collides add to the player score 
				# and pick new location for new orb
				p.score += 1

				mini = int(p.r)
				maxix = max(3 * int(p.r), self.width)
				maxiy = max(3 * int(p.r), self.height)

				xoff = randint(mini, maxix)
				if randint(0, 1) == 1:
					xoff *= -1
				yoff = randint(mini, maxiy)
				if randint(0, 1) == 1:
					yoff *= -1

				x, y = clip(x + xoff, 0, self.width * self.scale),\
					   clip(y + yoff, 0, self.height * self.scale)

				self.orbs[i] = (x, y, orb[2])
				break


		r = self.player_radius + (p.score - 10) ** (3/4) * 2
		p.r += (r - p.r) * 0.1


	def check_collisions(self, p):
		"""
		check if player p 
		has been eaten by someone else
		"""
		for player in self.players.values():
			if not p is player:
				diff = player.r - p.r
				if diff > 0.1 * p.r and self.collide(p.x, p.y, 0, player.x, player.y, diff):
					print('[INFO]', player.name, 'ate', p.name)
					player.score += p.score + 10
					p.score = 10
					p.update_pos(*self.pick_location())
					# p.update_pos(*self.cool_location())
					return True
		return False


	def cool_location(self):
		return self.width * self.scale - randint(100, 200), self.height * self.scale - randint(100, 200)


	def handle_client(self, conn):
		"""
		thread that handles it's client (player)
		"""
		name = self.receive(conn)
		print(f'[CLIENT] Client with name \"{name}\" has connected!')
		id = self.client_id

		self.send(conn, self.client_id)
		self.client_id += 1

		x, y = self.pick_location()
		# x, y = self.cool_location()
		color = self.pick_color()
		player = Player(x, y, color, self.player_radius, name, 10)
		self.players[id] = player
		self.send(conn, (x, y))

		while True:
    		# wait for position update
			if not (data := self.receive(conn)):
				break

			# update player position on the server
			player.update_pos(data[0], data[1])
			# check if player ate some orbs
			self.eat_orbs(player)
			# check if he died
			died = self.check_collisions(player)
			# send back the game info
			self.send_gameinfo(conn, died, player.score)

		conn.close()
		print(f'[CLIENT] Client with name \"{name}\" has disconnected!')
		del self.players[id]


	def send_gameinfo(self, conn, died, score):
		self.send(conn, (self.orbs, self.players, died, score))


server = Server()
server.start()

