import pygame as pg
import time, os
from network import Network
from camera import Camera
from math import sqrt, sin, cos, radians, pi
from pygame.math import Vector2 as vec2
from numpy import clip
from random import randint, random
from noise import pnoise2 as simplex
from input import InputBox, FONT
from hollow import textOutline


class FPS:

        def __init__(self):
                self.last = time.time()
                self.fps = 0

        def print(self):
                self.fps += 1
                now = time.time()
                if now - self.last > 1.0:
                        print('FPS', self.fps)
                        self.fps = 0
                        self.last = now



class Player:

        def __init__(self, x, y, color, r, name, score):
                self.x = x
                self.y = y
                self.color = color
                self.name = name
                self.score = score

        def update_pos(self, x, y):
                self.x = x
                self.y = y


class Game:

        def start(self):
                # initialize PyGame and UI (aquire name from user)
                print('[GAME] Initializing  PyGame!')
                self.pginit()
                self.menu()

                # establish connection to the server
                self.network = Network()
                self.network.connect(self.name)

                # initialize game logic things
                print('[GAME] Initializing game!')
                self.gameinit()

                # run the game
                print('[GAME] Running the game!')
                self.run()


        def get_id(self):
                """
                returns user id assinged by the server
                """
                return self.network.id


        def menu(self):
                box = InputBox(self.width // 2 - 100, self.height // 2 - 16, 100, 32)
                done, quitting = False, False
                agar_font = pg.font.SysFont('comicsans', 100)
                nick_font = pg.font.SysFont('comicsans', 50)
                agar_text = agar_font.render('Agar.bio', True, pg.Color('white'))
                nick_text = nick_font.render('Enter nickname:', True, pg.Color('white'))

                while not done:
                        for event in pg.event.get():
                                if event.type == pg.QUIT:
                                        quitting = True
                                if (name := box.handle_event(event)):
                                        if len(name) > 20:
                                                print('Name too long. Pick different one!')
                                        else:
                                                done = True

                        keys = pg.key.get_pressed()
                        if keys[pg.K_ESCAPE]:
                                quitting = True

                        if quitting:
                                print('[GAME] Quitting the game!')
                                pg.quit()
                                quit()

                        box.update()

                        self.win.fill((0, 0, 0))

                        box.draw(self.win)
                        self.win.blit(agar_text, (self.width // 2 - agar_text.get_width() // 2, 200))
                        self.win.blit(nick_text, (200, self.height // 2 - nick_text.get_height() // 2))

                        pg.display.flip()
                        self.clock.tick(30)

                self.name = name

        def pginit(self):
                self.width, self.height = 1280, 720
                pg.init()
                os.environ['SDL_VIDEO_CENTERED'] = '1'
                self.win = pg.display.set_mode((self.width, self.height))
                pg.display.set_caption('Agar.bio')
                self.clock = pg.time.Clock()

                self.lwidth, self.lheight = 200, 250
                self.lstart_x, self.lstart_y = self.width - self.lwidth - 20, 20
                self.lsurf = pg.Surface((self.lwidth, self.lheight))
                self.lsurf.set_alpha(100)
                self.lsurf.fill((0, 0, 0))

                self.swidth, self.sheight = 100, 50
                self.ssurf = pg.Surface((self.swidth, self.sheight))
                self.ssurf.set_alpha(100)
                self.lsurf.fill((0, 0, 0))


        def gameinit(self):
                self.fps = FPS()

                self.orb_radius = 10
                self.player_radius = 30
                self.scale = 5
                center = (self.width // 2 * self.scale, self.height // 2 * self.scale)

                #  self.pos = vec2(self.network.receive(1))
                #  self.pos = vec2(0, 0)
                self.pos = center
                self.vel = vec2(0, 0)
                self.speed = 200

                self.camera = Camera(self.width, self.height)
                self.camera.set_pos(center)

                pg.mouse.set_pos(self.width // 2, self.height // 2)

                self.name_font = pg.font.SysFont('comicsans', 50)
                self.leader_font = pg.font.SysFont('comicsans', 35)
                self.ui_font = pg.font.SysFont('comicsans', 25)

                self.elapsed = 0


        def run(self):
                self.run = True

                while self.run:
                        self.handle_events()
                        self.update()
                        self.draw()
                        self.fps.print()

                self.end()


        def handle_events(self):
                for event in pg.event.get():
                        if event.type == pg.QUIT:
                                self.run = False

                keys = pg.key.get_pressed()
                if keys[pg.K_ESCAPE]:
                        self.run = False

                mouse_pos = vec2(pg.mouse.get_pos())
                des_vel = (mouse_pos - vec2(self.camera.transform(*self.pos)))
                if des_vel.length() != 0:
                        mult = min(des_vel.length(), 200) / 100
                        des_vel = mult * des_vel.normalize()
                self.vel = self.vel.lerp(des_vel, 0.2)


        def update(self):
                # update time
                self.delta_time = self.clock.tick(120) * 0.001
                self.elapsed += self.delta_time

                # update position (based on user input)
                self.pos += self.vel * self.delta_time * self.speed
                self.pos.x = clip(self.pos.x, 0, self.width * self.scale)
                self.pos.y = clip(self.pos.y, 0, self.height * self.scale) 
                pos = (int(self.pos.x), int(self.pos.y))        
                
                # send my new position and get info about the board from the server
                self.orbs, self.players, died, self.score = self.send_update(pos)
                player = self.players[self.get_id()]

                # update my speed (if I ate sth - server tells me if I ate)
                factor = self.player_radius / player.r
                self.speed = sqrt(sqrt(factor)) * 200

                # if died reset position
                if died:
                        self.pos = vec2(player.x, player.y)

                # update camera zoom and position
                self.camera.set_pos(pos)
                scale = 1.5 * sqrt(self.player_radius / player.r)
                self.camera.set_scale(scale)


        def draw(self):
                self.win.fill((255, 255, 255))

                # draw background (drawing line in good scale just to trick you
                # that whole board is in lines - lines are only where you are)
                check_col, delta = (220, 220, 220), 60
                xoff = self.pos.x % delta
                ranx = int((self.width / 2 + self.camera.scale * xoff) / self.camera.scale / delta)

                for i in range(-ranx, ranx + 1):
                        x, _ = self.camera.transform(self.pos.x - xoff + i * delta, 0)
                        pg.draw.line(self.win, check_col, (x, 0), (x, self.height))

                yoff = self.pos.y % delta
                rany = int((self.height / 2 + self.camera.scale * yoff) / self.camera.scale / delta)

                for i in range(-rany, rany + 1):
                        _, y = self.camera.transform(0, self.pos.y - yoff + i * delta)
                        pg.draw.line(self.win, check_col, (0, y), (self.width, y))

                # draw orbs
                for x, y, color in self.orbs:
                        x, y = self.camera.transform(x, y)
                        r = self.camera.getr(self.orb_radius)
                        pg.draw.circle(self.win, color, (int(x), int(y)), int(r))

                # colors
                white = 255, 255, 255
                black = 10, 10, 10

                # draw players
                for p in sorted(self.players.values(), key=lambda p: p.r):
                        x, y = self.camera.transform(p.x, p.y)
                        r = self.camera.getr(p.r)
                        pg.draw.polygon(self.win, self.darken(p.color), self.get_circle(x, y, r))
                        pg.draw.polygon(self.win, p.color, self.get_circle(x, y, r - 10))
                        text = textOutline(self.name_font, p.name, white, black)
                        self.win.blit(text, (x - text.get_width() // 2, y - text.get_height() // 2))

                # draw leaderboard
                self.win.blit(self.lsurf, (self.lstart_x, self.lstart_y))

                text = self.leader_font.render('Leaderboard', True, white)
                self.win.blit(text, (self.lstart_x + self.lwidth // 2 - text.get_width() // 2, self.lstart_y + 10))

                board_len = min(len(self.players), 5)
                for i, p in enumerate(sorted(self.players.values(), key=lambda p: -p.score)[:board_len]):
                        text = self.ui_font.render(f'{i+1}. {p.name}', True, white)     
                        self.win.blit(text, (self.lstart_x + self.lwidth // 10, self.lstart_y + 50 + i * 20))

                # draw score
                text = self.ui_font.render(f'Score: {self.score}', True, white)
                size_x, size_y = text.get_size()
                sstart_x, sstart_y = 20, self.height - size_y - 20 

                dx, score = 75, self.score
                while score >= 100:
                        dx += 10
                        score //= 10

                size = self.ssurf.get_size()
                if size[0] != dx + 10:
                        self.ssurf = pg.transform.scale(self.ssurf, (dx + 10, size_y + 10))

                self.win.blit(self.ssurf, (sstart_x, sstart_y))
                self.win.blit(text, (sstart_x + 5, sstart_y + 5))

                pg.display.flip()


        def get_circle(self, xoff, yoff, r, dalfa = 5):
                """
                returns points of noisy circle
                """
                angle, delta = 0, radians(dalfa)
                points, seed = [], self.elapsed * 2
                while angle < 2 * pi:
                        x, y = cos(angle), sin(angle)
                        rad = r + (r ** (3/4)) * 0.1 * simplex(2 * x + seed, 2 * y + seed)
                        points.append((int(x * rad + xoff), int(y * rad + yoff)))
                        angle += delta
                return points


        def darken(self, color):
                r, g, b = color
                mult = 0.85
                return (int(mult * r), int(mult * g), int(mult * b))


        def send_update(self, pos):
                """
                send position update to the server
                and receive board info in return
                """
                return self.network.send(pos)


        def end(self):
                print('[GAME] Quitting the game!')
                pg.quit()
                self.network.disconnect()


game = Game()
game.start()
