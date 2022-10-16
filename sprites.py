import time

import pygame
from config import *
import math
import random
from _thread import *


class Spritesheet:
    def __init__(self, file):
        self.sheet = pygame.image.load(file).convert()

    def get_sprite(self, x, y, width, height):
        sprite = pygame.Surface([width, height])
        sprite.blit(self.sheet, (0, 0), (x, y, width, height))
        sprite.set_colorkey(BLACK)
        return sprite


class Player(pygame.sprite.Sprite):
    def __init__(self, game, x, y, playerID, character, typeParam):
        self.game = game
        self._layer = PLAYER_LAYER
        self.groups = self.game.all_sprites
        pygame.sprite.Sprite.__init__(self, self.groups)

        self.playerIdInServer = playerID

        self.x = x * TILESIZE
        self.y = y * TILESIZE
        self.width = TILESIZE
        self.height = TILESIZE
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

        self.character = character
        self.pnx = 0  # offset em x para o player n na imagem
        self.pny = 0  # offset em y para o player n na imagem
        self.selectCharacter()

        self.dx = 0
        self.dy = 0

        self.direction = "standing"

        self.movementSpeed = MOVEMENT_SPEED
        self.animation_loop = 1

        self.lives = True

        # Local ou Server
        self.type = typeParam

        # Server Room
        self.roomID = None

        # Animations
        self.down_animations = []
        self.up_animations = []
        self.left_animations = []
        self.right_animations = []
        self.still_animation = self.game.character_spritesheet.get_sprite(3 * TILESIZE * self.pnx + 32,
                                                                          2 + 4 * TILESIZE * self.pny, self.width,
                                                                          self.height)
        self.image = self.game.character_spritesheet.get_sprite(3 * TILESIZE * self.pnx + 32,
                                                                2 + 4 * TILESIZE * self.pny, self.width, self.height)

        # Key Map
        self.keyMap = [
            [pygame.K_RIGHT, pygame.K_LEFT, pygame.K_UP, pygame.K_DOWN],  # player 0 keys
            [pygame.K_d, pygame.K_a, pygame.K_w, pygame.K_s]]  # player 1 keys

        # Space
        self.control = [False]

    def setRoom(self, roomID):
        self.roomID = roomID

    def selectCharacter(self):
        pn = self.character
        pos = [[1, 2, 3, 4],
               [5, 6, 7, 8]
               ]
        self.pnx = 0
        self.pny = 0
        for i, row in enumerate(pos):
            for j, column in enumerate(row):
                if column == pn:
                    self.pnx = j
                    self.pny = i
                    return

    def draw(self, window):
        pygame.draw.rect(window, self.color, self.rect)

    def update(self):
        if self.type == "local":
            self.controls()

    def collideBlocks(self, direction):
        if direction == "x":
            hits = pygame.sprite.spritecollide(self, self.game.blocks, False)
            if hits:
                if self.dx > 0:
                    self.rect.x = hits[0].rect.left - self.rect.width
                else:
                    self.rect.x = hits[0].rect.right

        if direction == "y":
            hits = pygame.sprite.spritecollide(self, self.game.blocks, False)
            if hits:
                if self.dy > 0:
                    self.rect.y = hits[0].rect.top - self.rect.height
                else:
                    self.rect.y = hits[0].rect.bottom

    def collideExplosion(self):
        # collide with explosion
        hits = pygame.sprite.spritecollide(self, self.game.weapons, False)
        if hits and self.alive():
            self.kill()
            self.game.client.deletePlayer(self.playerIdInServer)
            print("REQUEST DELETE")
            self.lives = False

    def controls(self):
        self.direction = "standing"

        keys = pygame.key.get_pressed()
        # up
        if keys[self.keyMap[0][2]]:
            self.dy = -self.movementSpeed
            self.direction = "up"

        # down
        if keys[self.keyMap[0][3]]:
            self.dy = +self.movementSpeed
            self.direction = "down"

        # right
        if keys[self.keyMap[0][0]]:
            self.dx = +self.movementSpeed
            self.direction = "right"

        # left
        if keys[self.keyMap[0][1]]:
            self.dx = -self.movementSpeed
            self.direction = "left"

        # throw bomb
        if keys[pygame.K_SPACE]:
            if not self.control[0]:
                start_new_thread(self.game.createBomb, (self.x, self.y))
                self.control[0] = True
        else:
            self.control[0] = False

        if keys[pygame.K_j] and self.lives:
            player = self.game.players[0]
            self.game.players.remove(player)
            player.kill()
            self.game.client.deletePlayer(self.playerIdInServer)
            self.lives = False

        if self.type == "local":
            self.rect.y += self.dy
            self.collideBlocks("y")
            self.rect.x += self.dx
            self.collideBlocks("x")

        self.x = self.rect.x
        self.y = self.rect.y

        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        # print("Player "+str(self.playerIdInServer)+" direction: "+str(self.direction))
        # self.animate()

        self.dx = 0
        self.dy = 0

    def animate(self):
        self.all_animations = []

        for j in range(4):
            self.aux_animation = []
            for i in range(3):
                self.aux_animation.append(self.game.character_spritesheet.get_sprite(3 * TILESIZE * self.pnx + 32 * i,
                                                                                     2 + 4 * TILESIZE * self.pny + 32 * j,
                                                                                     self.width, self.height))
            self.all_animations.append(self.aux_animation)

        self.down_animations = self.all_animations[0]
        self.left_animations = self.all_animations[1]
        self.right_animations = self.all_animations[2]
        self.up_animations = self.all_animations[3]

        # Standing still
        if self.direction == "standing":
            self.animation_loop = 1
            self.image = self.still_animation

        # Moving down
        if self.direction == "down":
            self.image = self.down_animations[math.floor(self.animation_loop)]
            self.animation_loop += ANIMATION_SPEED / FRAMERATE
            if self.animation_loop >= 3:
                self.animation_loop = 1

        # Moving up
        if self.direction == "up":
            self.image = self.up_animations[math.floor(self.animation_loop)]
            self.animation_loop += ANIMATION_SPEED / FRAMERATE
            if self.animation_loop >= 3:
                self.animation_loop = 1

        # Moving right
        if self.direction == "right":
            self.image = self.right_animations[math.floor(self.animation_loop)]
            self.animation_loop += ANIMATION_SPEED / FRAMERATE
            if self.animation_loop >= 3:
                self.animation_loop = 1

        # Moving left
        if self.direction == "left":
            self.image = self.left_animations[math.floor(self.animation_loop)]
            self.animation_loop += ANIMATION_SPEED / FRAMERATE
            if self.animation_loop >= 3:
                self.animation_loop = 1


class Block(pygame.sprite.Sprite):
    def __init__(self, game, x, y, px, py):
        self.game = game
        self._layer = BLOCK_LAYER
        self.groups = self.game.all_sprites, self.game.blocks

        self.x = x * TILESIZE
        self.y = y * TILESIZE
        self.width = TILESIZE
        self.height = TILESIZE
        self.image = self.game.terrain_spritesheet.get_sprite(px, py, self.width, self.height)
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)


class Rock(Block):
    def __init__(self, game, x, y):
        Block.__init__(self, game, x, y, 960, 448)
        pygame.sprite.Sprite.__init__(self, self.groups)


class Bush(Block):
    def __init__(self, game, x, y):
        Block.__init__(self, game, x, y, 543, 352)
        pygame.sprite.Sprite.__init__(self, self.groups)


class SquareLimit(Block):
    def __init__(self, game, x, y):
        # Block.__init__(self, game, x, y, 96, 408)
        Block.__init__(self, game, x, y, 104, 400)
        pygame.sprite.Sprite.__init__(self, self.groups)


class Ground(pygame.sprite.Sprite):
    def __init__(self, game, x, y, px, py):
        self.game = game
        self._layer = GROUND_LAYER
        self.groups = self.game.all_sprites
        pygame.sprite.Sprite.__init__(self, self.groups)

        self.x = x * TILESIZE
        self.y = y * TILESIZE
        self.width = TILESIZE
        self.height = TILESIZE

        self.image = self.game.terrain_spritesheet.get_sprite(px, py, self.width, self.height)
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)


class Grass(Ground):
    def __init__(self, game, x, y):
        Ground.__init__(self, game, x, y, 64, 352)
        pygame.sprite.Sprite.__init__(self, self.groups)


class Sand(Ground):
    def __init__(self, game, x, y):
        Ground.__init__(self, game, x, y, 576, 352)
        pygame.sprite.Sprite.__init__(self, self.groups)


# 352, 480
class Brick(Ground):
    def __init__(self, game, x, y):
        Ground.__init__(self, game, x, y, 352, 480)
        pygame.sprite.Sprite.__init__(self, self.groups)


class BlueRock(Ground):
    def __init__(self, game, x, y):
        Ground.__init__(self, game, x, y, 224, 511)
        pygame.sprite.Sprite.__init__(self, self.groups)


# class Sand(Ground):
#    def __init__(self, game, x, y):
#        Ground.__init__(self, game, x, y, 576, 352)
#        pygame.sprite.Sprite.__init__(self, self.groups)


class Weapon(pygame.sprite.Sprite):
    def __init__(self, game, x, y, px, py):
        self.game = game
        self._layer = WEAPON_LAYER
        self.groups = self.game.all_sprites, self.game.weapons
        pygame.sprite.Sprite.__init__(self, self.groups)

        self.x = x * TILESIZE
        self.y = y * TILESIZE
        self.width = TILESIZE
        self.height = TILESIZE

        self.image = self.game.terrain_spritesheet.get_sprite(px, py, self.width, self.height)
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)


# class Fire(Weapon):
#    def __init__(self, game, x, y):
#        Weapon.__init__(self, game, x, y, 480 + TILESIZE*int(random.randint(0, 2)), 160)
#        pygame.sprite.Sprite.__init__(self, self.groups)

class Fire(pygame.sprite.Sprite):
    def __init__(self, game, x, y):
        self.game = game
        self._layer = WEAPON_LAYER
        self.groups = self.game.all_sprites, self.game.weapons
        pygame.sprite.Sprite.__init__(self, self.groups)

        self.x = x * TILESIZE
        self.y = y * TILESIZE
        self.width = TILESIZE
        self.height = TILESIZE

        self.image = self.game.terrain_spritesheet.get_sprite(480 + TILESIZE * int(random.randint(0, 2)), 160,
                                                              self.width, self.height)
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

        self.inittime = pygame.time.get_ticks()


class Bomb(pygame.sprite.Sprite):
    def __init__(self, game, x, y, index):
        self.game = game
        self._layer = WEAPON_LAYER
        self.groups = self.game.all_sprites
        pygame.sprite.Sprite.__init__(self, self.groups)

        self.index = index

        self.x = x
        self.y = y
        self.width = TILESIZE
        self.height = TILESIZE

        # bomb coordinates
        # 1,1 - 62, 55
        # 2,1 - 137, 54
        # 1,2 - 62, 99

        self.image = self.game.bomb_spritesheet.get_sprite(32, 23, self.width, self.height)
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

        self.inittime = pygame.time.get_ticks()


class SequenceAnalyzer:
    def __init__(self, match_sequence):
        self.sequence = []
        # sequence is given from right to left (t0 to tF)
        self.match_sequence = match_sequence

    def analyze(self, element):
        if len(self.sequence) < len(self.match_sequence):
            self.sequence.append(element)
        else:
            if self.sequence[len(self.sequence) - 1] != element:
                self.sequence.remove(self.sequence[0])
                self.sequence.append(element)
            else:
                return False

        if len(self.sequence) == len(self.match_sequence):
            for index, element in enumerate(self.sequence):
                if element != self.match_sequence[index]:
                    # Sequences doesnt match
                    return False
            # Sequences does match
            return True
        else:
            # Sequences doesnt match
            return False
        return False


class Button:
    def __init__(self, x, y, w, h, fg, bg, content, fontsize):
        self.font = pygame.font.Font('Indigo Regular.otf', fontsize)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.fg = fg
        self.bg = bg
        self.content = content
        self.fontsize = fontsize

        self.image = pygame.Surface((self.w, self.h))
        self.image.fill(self.bg)
        self.rect = self.image.get_rect()

        self.rect.x = self.x
        self.rect.y = self.y

        self.text = self.font.render(self.content, True, self.fg)
        self.text_rect = self.text.get_rect(center=(self.w / 2, self.h / 2))
        self.image.blit(self.text, self.text_rect)

        self.sequence_analyzer = SequenceAnalyzer([False, True, False])

    def clickSequenceAnalyze(self, pos, pressed):
        return self.sequence_analyzer.analyze(self.is_pressed(pos, pressed)) and self.rect.collidepoint(pos)

    def is_pressed(self, pos, pressed):
        if self.rect.collidepoint(pos):
            if pressed[0]:
                return True
        return False


class TextField:
    def __init__(self, x, y, w, h, fg, bg, content, fontsize):
        self.font = pygame.font.Font('Indigo Regular.otf', fontsize)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.fg = fg
        self.bg = bg
        self.content = content
        self.fontsize = fontsize

        self.isTyping = False
        self.default_text_changed = False

        self.image = pygame.Surface((self.w, self.h))
        self.image.fill(self.bg)
        self.rect = self.image.get_rect()

        self.rect.x = self.x
        self.rect.y = self.y

        self.text = self.font.render(self.content, True, self.fg)
        self.text_rect = self.text.get_rect(center=(self.w / 2, self.h / 2))
        self.image.blit(self.text, self.text_rect)

        self.sequence_analyzer = SequenceAnalyzer([False, True, False])

    def handleKeydownEvent(self, pressed, key_text_value):
        if self.isTyping:
            # If its a single character
            if len(key_text_value) == 1:
                self.appendChar(key_text_value)

            # Handle space pressed
            if pressed[pygame.K_SPACE]:
                self.appendChar(' ')

            # Handle backspace pressed
            if pressed[pygame.K_BACKSPACE]:
                self.backspace()

    def setText(self, text):
        self.updateContent(text)
        self.image.blit(self.text, self.text_rect)

    def updateContent(self, content):
        self.content = content
        self.image = pygame.Surface((self.w, self.h))
        self.image.fill(self.bg)
        self.rect = self.image.get_rect()
        self.rect.x = self.x
        self.rect.y = self.y
        self.text = self.font.render(self.content, True, self.fg)
        self.text_rect = self.text.get_rect(center=(self.w / 2, self.h / 2))

    def appendChar(self, char):
        text = self.content + char
        self.setText(text)

    def backspace(self):
        self.setText(self.deleteLastStringElement(self.content))

    def clickSequenceAnalyze(self, pos, pressed):
        return self.sequence_analyzer.analyze(self.is_pressed(pos, pressed)) and self.rect.collidepoint(pos)

    def is_pressed(self, pos, pressed):
        if self.rect.collidepoint(pos):
            if pressed[0]:
                return True
        return False

    def is_typing(self, pos, pressed):
        if not self.is_pressed(pos, pressed) and pressed[0]:
            self.isTyping = False
        else:
            if self.is_pressed(pos, pressed):
                self.isTyping = True
                if not self.default_text_changed:
                    self.setText('')
                    self.default_text_changed = True
        return self.isTyping

    def deleteLastStringElement(self, input_string):
        input_string = input_string[:max(len(input_string) - 2, 0)]
        return input_string


class ListField:
    def __init__(self, x, y, w, h, fg, bg, content, fontsize):
        self.font = pygame.font.Font('Indigo Regular.otf', fontsize)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.fg = fg
        self.bg = bg
        self.content = content
        self.fontsize = fontsize