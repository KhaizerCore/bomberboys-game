import sys
import threading

import pygame
from config import *
from sprites import *
from client import *
import json
import math
import time
from threading import Thread
from threading import Event
from datetime import datetime
import os


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Client")

        self.screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
        self.clock = pygame.time.Clock()  # FRAMERATE
        self.running = True

        self.character_spritesheet = Spritesheet('img/rsz_multipleCharacters.png')
        self.terrain_spritesheet = Spritesheet('img/terrain.png')
        self.bomb_spritesheet = Spritesheet('img/Explosion/bombs.png')
        self.explosion_spritesheet = Spritesheet('img/Explosion/explosionEffect.png')

        self.myPlayer = None
        self.players = []
        self.Lock = False

        self.bombs = []
        self.explosions = []

        self.client = Client()

        self.font = pygame.font.Font('Indigo Regular.otf', 32)
        self.intro_background = pygame.image.load('img/background.png')

        # Stack for Screens
        self.screenStack = Stack()

        # Initialize room parameters
        self.roomOp = 0
        self.room_name = None
        self.room_password = None
        self.room_capacity = 4

    def acquire(self):
        while self.Lock:
            pass
        self.Lock = True

    def release(self):
        self.Lock = False

    def requestRoom(self, playerGUID):
        # roomOp = int(input("Autojoin (0); Create Room (1); Join Specific Room (2): "))
        roomID = -1

        # Autojoin
        if self.roomOp == 0:
            pass

        # Create Room
        if self.roomOp == 1:
            pass
            # name = input("Room name: ")
            # password = input("Password: ")

        # Join Specific Room
        if self.roomOp == 2:
            print("ALL ROOMS")
            print(self.client.requestAllRooms(), end='\n')
            name = input("Room name: ")
            password = input("Password: ")
            roomID = self.client.joinSpecificRoom(name, password, playerGUID)

        return roomID

    def createLocalPlayer(self, x, y):
        character = random.randint(0, 7)
        playerGUID = self.client.getPlayerID()
        self.myPlayer = Player(self, x, y, playerGUID, character, "local")
        self.players.append(self.myPlayer)
        # Request Server to Create Player
        self.client.createPLayer(x, y, character, playerGUID)

    def createBomb(self, x, y):
        bombID = self.client.createBomb(x, y, self.myPlayer.playerIdInServer, self.myPlayer.roomID)
        self.bombs.append(Bomb(self, x, y, bombID))
        # print(len(self.bombs))

    def createExplosion(self, x, y, radius):
        keep_up = True
        keep_down = True
        keep_left = True
        keep_right = True
        actual_radius = 1
        xAdjusted = x / TILESIZE
        yAdjusted = y / TILESIZE
        explosion = [pygame.time.get_ticks(), Fire(self, xAdjusted, yAdjusted)]
        while actual_radius <= radius and actual_radius != 0:
            # hit = pygame.sprite.spritecollide(self, self.game.blocks, True)
            if keep_right:
                fire = Fire(self, xAdjusted + actual_radius, yAdjusted)
                if pygame.sprite.spritecollide(fire, self.blocks, False):
                    fire.kill()
                    keep_right = False
                else:
                    explosion.append(fire)

            if keep_left:
                fire = Fire(self, xAdjusted - actual_radius, yAdjusted)
                if pygame.sprite.spritecollide(fire, self.blocks, False):
                    fire.kill()
                    keep_left = False
                else:
                    explosion.append(fire)

            if keep_up:
                fire = Fire(self, xAdjusted, yAdjusted + actual_radius)
                if pygame.sprite.spritecollide(fire, self.blocks, False):
                    fire.kill()
                    keep_up = False
                else:
                    explosion.append(fire)

            if keep_down:
                fire = Fire(self, xAdjusted, yAdjusted - actual_radius)
                if pygame.sprite.spritecollide(fire, self.blocks, False):
                    fire.kill()
                    keep_down = False
                else:
                    explosion.append(fire)

            actual_radius += 1
            self.explosions.append(explosion)
        self.acquire()
        self.myPlayer.collideExplosion()
        self.release()

    def removeBomb(self, bomb):
        self.acquire()
        self.bombs.remove(bomb)
        self.release()
        self.createExplosion(bomb.x, bomb.y, BOMB_RADIUS)
        bomb.kill()

    def removeExplosion(self, explosion):
        self.acquire()
        self.explosions.remove(explosion)
        self.release()
        for fire in explosion:
            if type(fire) is not int:
                fire.kill()

    def removePlayer(self, playerID):
        for player in self.players:
            if player.playerIdInServer == playerID and player.alive():
                self.acquire()
                player.kill()
                self.release()

    def checkElements(self):
        # check bomb explosion countdown
        for bomb in self.bombs:
            bomb_time = pygame.time.get_ticks() - bomb.inittime
            animation_index = 0
            step = BOMB_TIME_FUSE * 1000 / 6

            xdist = 75

            if step * 0 <= bomb_time < step * 1:
                bomb.image = self.bomb_spritesheet.get_sprite(32 + xdist * 0, 23, bomb.width, bomb.height)
                animation_index += 1

            if step * 1 <= bomb_time < step * 2:
                bomb.image = self.bomb_spritesheet.get_sprite(32 + xdist * 1, 23, bomb.width, bomb.height)
                animation_index += 1

            if step * 2 <= bomb_time < step * 3:
                bomb.image = self.bomb_spritesheet.get_sprite(32 + xdist * 2, 23, bomb.width, bomb.height)
                animation_index += 1

            if step * 3 <= bomb_time < step * 4:
                animation_index = 0
                bomb.image = self.bomb_spritesheet.get_sprite(32 + xdist * 0, 98, bomb.width, bomb.height)
                animation_index += 1

            if step * 4 <= bomb_time < step * 5:
                bomb.image = self.bomb_spritesheet.get_sprite(32 + xdist * 1, 98, bomb.width, bomb.height)
                animation_index += 1

            if step * 5 <= bomb_time < step * 6:
                bomb.image = self.bomb_spritesheet.get_sprite(32 + xdist * 2, 98, bomb.width, bomb.height)
                animation_index += 1

            if pygame.time.get_ticks() - bomb.inittime >= BOMB_TIME_FUSE * 1000:
                self.removeBomb(bomb)

        # check explosions countdown
        for explosion in self.explosions:
            explosion_time = pygame.time.get_ticks() - explosion[0]

            for fire in explosion:
                if type(fire) is not int:
                    animation_index = 0
                    step = EXPLOSION_DURATION * 1000 / 5
                    xdist = 32

                    if step * 0 <= explosion_time < step * 1:
                        fire.image = self.explosion_spritesheet.get_sprite(0 + xdist * 0, 32, TILESIZE, TILESIZE)
                        animation_index += 1

                    if step * 1 <= explosion_time < step * 2:
                        fire.image = self.explosion_spritesheet.get_sprite(0 + xdist * 2, 32, TILESIZE, TILESIZE)
                        animation_index += 1

                    if step * 2 <= explosion_time < step * 3:
                        fire.image = self.explosion_spritesheet.get_sprite(0 + xdist * 4, 32, TILESIZE, TILESIZE)
                        animation_index += 1

                    if step * 3 <= explosion_time < step * 4:
                        animation_index = 0
                        fire.image = self.explosion_spritesheet.get_sprite(0 + xdist * 0, 32, TILESIZE, TILESIZE)
                        animation_index += 1

                    if step * 4 <= explosion_time < step * 5:
                        fire.image = self.explosion_spritesheet.get_sprite(0 + xdist * 2, 32, TILESIZE, TILESIZE)
                        animation_index += 1

                    if step * 5 <= explosion_time < step * 6:
                        fire.image = self.explosion_spritesheet.get_sprite(0 + xdist * 4, 32, TILESIZE, TILESIZE)
                        animation_index += 1

            if explosion_time >= EXPLOSION_DURATION * 1000:
                self.removeExplosion(explosion)

    def createTileMap(self):
        for i, row in enumerate(tilemap):
            for j, column in enumerate(row):
                BlueRock(self, j, i)
                if column == "R":
                    SquareLimit(self, j, i)
                if column == "P":
                    self.createLocalPlayer(j, i)
                if column == "B":
                    Bush(self, j, i)
                if column == "F":
                    Fire(self, j, i)

    def updatePlayerPosition(self):
        self.client.setPlayerPosition(self.myPlayer.playerIdInServer, self.myPlayer.x, self.myPlayer.y,
                                      self.myPlayer.direction, self.myPlayer.roomID)

    def getServerParameters(self):
        jsondataarray = json.loads(
            self.client.getServerParameters(self.myPlayer.playerIdInServer, self.myPlayer.roomID))
        if jsondataarray:
            for jsondata in jsondataarray:
                exists = False
                for j in self.players:
                    if jsondata['id'] == j.playerIdInServer:
                        exists = True
                        j.dx = jsondata['x'] - j.rect.x
                        j.dy = jsondata['y'] - j.rect.y
                        j.rect.x = jsondata['x']
                        j.rect.y = jsondata['y']
                        j.direction = jsondata['direction']
                if not exists:
                    self.players.append(
                        Player(self, math.floor(jsondata['x'] / TILESIZE), math.floor(jsondata['y'] / TILESIZE),
                               jsondata['id'], jsondata['character'], "server"))
                    print("Player " + str(self.players[len(self.players) - 1].playerIdInServer) + " criado")

    def getServerCommands(self):
        commandArray = self.client.getServerCommands(self.myPlayer.playerIdInServer, self.myPlayer.roomID)
        # print(commandArray)
        if commandArray:
            for command in commandArray:
                self.decodeCommand(command)

    def decodeCommand(self, command):
        if command:
            if command[0] == "DELETE":

                if command[1] == "PLAYER":
                    self.removePlayer(command[2])

            if command[0] == "CREATE":

                if command[1] == "BOMB":
                    x = command[2]
                    y = command[3]
                    bombID = command[5]
                    self.bombs.append(Bomb(self, x, y, bombID))

    def sendServerParameters(self, event):
        while self.running:
            if self.myPlayer.alive():
                self.updatePlayerPosition()
            event.wait(1 / 50)

    def connectionUpdates(self, event):
        c = 0
        while self.running:
            self.getServerParameters()
            if c > 2:
                self.getServerCommands()
                c = 0
            else:
                c += 1
                event.wait(1 / 100)

    def establishConnection(self):
        event = threading.Event()
        t1 = threading.Thread(target=self.connectionUpdates, args=(event,))
        t2 = threading.Thread(target=self.sendServerParameters, args=(event,))
        t1.start()
        t2.start()

    def new(self):
        # a new game starts
        self.playing = True

        self.all_sprites = pygame.sprite.LayeredUpdates()
        self.blocks = pygame.sprite.LayeredUpdates()
        self.enemies = pygame.sprite.LayeredUpdates()
        self.attacks = pygame.sprite.LayeredUpdates()
        self.weapons = pygame.sprite.LayeredUpdates()

        # self.player = Player(self, 1, 2, WHITE)
        self.createTileMap()

    def events(self):
        # game loop events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.playing = False
                self.running = False
                pygame.QUIT

    def animate_all(self):
        for player in self.players:
            player.animate()

    def update(self):
        self.checkElements()
        # game loop updates
        self.all_sprites.update()
        # self.updatePlayerPosition()
        self.animate_all()

    def draw(self):
        # game loop draw
        self.acquire()
        self.all_sprites.draw(self.screen)
        self.release()
        self.clock.tick(FRAMERATE)
        pygame.display.update()

    def gameOver(self):
        pass

    def introScreen(self):
        intro_screen = IntroScreen(self)
        Navigator(intro_screen).gotoScreen(intro_screen)

    def runEngine(self):
        # game loop
        while self.playing:
            self.events()
            self.update()
            self.draw()
        self.running = False


class Navigator:
    def __init__(self, actual_screen):
        self.actual_screen = actual_screen

    def gotoScreen(self, screen):
        self.actual_screen.game.screenStack.push(screen)
        screen.draw()
        self.actual_screen.running = False

    def returnScreen(self):
        self.actual_screen.game.screenStack.pop()
        self.actual_screen.game.screenStack.top().draw()
        self.actual_screen.running = False


class Screen:
    def __init__(self, game):
        self.game = game
        self.running = True
        self.navigator = Navigator(self)

        self.buttons = []
        self.textFields = []

    def blitButtons(self):
        for index, element in enumerate(self.buttons):
            self.game.screen.blit(element.image, element.rect)

    def blitTextFields(self):
        for index, element in enumerate(self.textFields):
            self.game.screen.blit(element.image, element.rect)

    def blitAllElements(self):
        self.blitButtons()
        self.blitTextFields()

    def addButton(self, button):
        self.buttons.append(button)
        return button

    def removeButton(self, button):
        self.buttons.remove(button)
        return button

    def addTextField(self, text_field):
        self.textFields.append(text_field)
        return text_field

    def removeTextField(self, text_field):
        self.textFields.remove(text_field)
        return text_field

    # Tests if textField is in typing mode (also testing and handling if the text field is clicked).
    # For all textFields.
    def updateTextFieldsTypingController(self, mouse_pos, mouse_pressed):
        for textField in self.textFields:
            textField.is_typing(mouse_pos, mouse_pressed)

    # Passes keyboard pressed array (from pygame) + text value referent to the pressed key. For all textFields.
    def notifyTextFieldsKeydownEvent(self, pressed, key_text_value):
        for textField in self.textFields:
            textField.handleKeydownEvent(pressed, key_text_value)

    def deleteAllTextFields(self):
        self.textFields = []

    def elementExists(self, element, array):
        for el in array:
            if el == element:
                return True
        return False


class IntroScreen(Screen):
    def __init__(self, game):
        # Initialize super class
        super().__init__(game)

        self.title = self.game.font.render('DSGame', True, BLACK)
        self.title_rect = self.title.get_rect(x=math.floor(WIN_WIDTH / 2) - math.floor(self.title.get_width() / 2),
                                              y=10)
        self.play_button = self.addButton(
            Button(math.floor(WIN_WIDTH / 2 - 50), math.floor(WIN_HEIGHT / 2 - 100), 100, 50, WHITE,
                   BLACK, 'Jogar', 32))
        self.quit_button = self.addButton(
            Button(math.floor(WIN_WIDTH / 2 - 50), math.floor(WIN_HEIGHT / 2 + 20), 100, 50, WHITE,
                   BLACK, 'Sair', 32))

    def draw(self):
        self.running = True
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.game.running = False

            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()

            self.game.screen.blit(self.game.intro_background, (0, 0))
            self.game.screen.blit(self.title, self.title_rect)
            self.blitAllElements()
            self.game.clock.tick(FRAMERATE)
            pygame.display.update()

            if self.play_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                self.navigator.gotoScreen(LoginScreen(self.game))

            if self.quit_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                self.running = False
                self.game.running = False
                self.game.playing = False
                pygame.quit()


class LoginScreen(Screen):
    def __init__(self, game):
        # Initialize super class
        super().__init__(game)

        self.title = self.game.font.render('DSGame', True, BLACK)
        self.title_rect = self.title.get_rect(x=math.floor(WIN_WIDTH / 2) - math.floor(self.title.get_width() / 2),
                                              y=10)

        self.return_button = self.addButton(Button(20, 20, 60, 30, WHITE, BLACK, 'ret', 32))

        self.login_button = self.addButton(
            Button(math.floor(2 * WIN_WIDTH / 3 - 150/2), math.floor(3 * WIN_HEIGHT / 4) - 60 , 150, 50, WHITE, BLACK, 'Login', 32))

        self.register_button = self.addButton(
            Button(math.floor(2 * WIN_WIDTH / 3 - 150/2) , math.floor(3 * WIN_HEIGHT / 4 ) + 20, 150, 50, WHITE, BLACK, 'Registro', 32))

        self.username_text = self.addTextField(
            TextField(math.floor(WIN_WIDTH / 2 - 150), math.floor(WIN_HEIGHT / 3) - 50, 300, 50, BLACK, WHITE, 'Username', 24))

        self.password_text = self.addTextField(
            TextField(math.floor(WIN_WIDTH / 2 - 150), math.floor( WIN_HEIGHT / 3) + 50, 300, 50, BLACK, WHITE, 'Senha', 24))

    def draw(self):
        self.running = True
        while self.running:
            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()

            self.game.screen.blit(self.game.intro_background, (0, 0))
            self.game.screen.blit(self.title, self.title_rect)
            self.blitAllElements()
            self.game.clock.tick(FRAMERATE)
            pygame.display.update()

            # Tests if username_text or password_text is in typing mode (also testing and handling if the text field
            # is clicked)
            self.updateTextFieldsTypingController(mouse_pos, mouse_pressed)

            if self.return_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                self.navigator.returnScreen()
                self.running = False

            if self.login_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                username = self.username_text.content
                password = self.password_text.content

                queryCode = self.game.client.requestLogin(username, password)
                if queryCode == 1:
                    text_field_width = 500
                    text_field_height = 50
                    self.addTextField(
                        TextField(math.floor(WIN_WIDTH / 2 - text_field_width / 2), self.password_text.y + self.password_text.h + 50,
                                  text_field_width, text_field_height, WHITE, SUCCESS_COLOR, 'Sucesso no Login!',
                                  24))

                    self.removeButton(self.login_button)
                    self.removeButton(self.register_button)

                    self.game.screen.blit(self.game.intro_background, (0, 0))
                    self.game.screen.blit(self.title, self.title_rect)
                    self.blitAllElements()
                    self.game.clock.tick(FRAMERATE)
                    pygame.display.update()

                    time.sleep(2);

                    self.navigator.gotoScreen(ConnectionOptionScreen(self.game))

                else:
                    text_field_width = 500
                    text_field_height = 50
                    self.addTextField(
                        TextField(math.floor(WIN_WIDTH / 2 - text_field_width / 2), self.password_text.y + self.password_text.h + 50,
                                  text_field_width, text_field_height, WHITE, WARNING_COLOR, 'Impossivel logar', 24))

            if self.register_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                self.navigator.gotoScreen(RegisterScreen(self.game))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.game.running = False

                if event.type == pygame.KEYDOWN:
                    pressed = pygame.key.get_pressed()
                    key_text_value = str(event.unicode)

                    # Will notify all text fields that an input has been received.
                    self.notifyTextFieldsKeydownEvent(pressed, key_text_value)


class RegisterScreen(Screen):
    def __init__(self, game):
        # Initialize super class
        super().__init__(game)

        self.title = self.game.font.render('DSGame', True, BLACK)
        self.title_rect = self.title.get_rect(x=math.floor(WIN_WIDTH / 2) - math.floor(self.title.get_width() / 2),
                                              y=10)

        self.return_button = self.addButton(Button(20, 20, 60, 30, WHITE, BLACK, 'ret', 32))

        self.create_account_button = self.addButton(
            Button(math.floor(2 * WIN_WIDTH / 3 - 150/2), math.floor(3 * WIN_HEIGHT / 4) + 20, 380, 50, WHITE, BLACK, 'Criar Conta', 32))

        self.username_text = self.addTextField(
            TextField(math.floor(WIN_WIDTH / 2 - 150), math.floor(WIN_HEIGHT / 3) - 50, 300, 50, BLACK, WHITE, 'Username', 24))

        self.email_text = self.addTextField(
            TextField(math.floor(WIN_WIDTH / 2 - 150), math.floor( WIN_HEIGHT / 3) + 50, 300, 50, BLACK, WHITE, 'E-mail', 24))

        self.password_text = self.addTextField(
            TextField(math.floor(WIN_WIDTH / 2 - 150), math.floor(WIN_HEIGHT / 3) + 150, 300, 50, BLACK, WHITE, 'Senha',
                      24))

    def draw(self):
        self.running = True
        while self.running:
            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()

            self.game.screen.blit(self.game.intro_background, (0, 0))
            self.game.screen.blit(self.title, self.title_rect)
            self.blitAllElements()
            self.game.clock.tick(FRAMERATE)
            pygame.display.update()

            # Tests if username_text or password_text is in typing mode (also testing and handling if the text field
            # is clicked)
            self.updateTextFieldsTypingController(mouse_pos, mouse_pressed)

            if self.return_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                self.navigator.returnScreen()
                self.running = False

            if self.create_account_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                username = self.username_text.content
                email = self.email_text.content
                password = self.password_text.content

                queryCode = self.game.client.requestRegisterAccount(username, email, password)
                if queryCode == 1:
                    text_field_width = 500
                    text_field_height = 50
                    self.addTextField(
                        TextField(math.floor(WIN_WIDTH / 2 - text_field_width / 2), self.password_text.y + self.password_text.h + 50,
                                  text_field_width, text_field_height, WHITE, SUCCESS_COLOR, 'Conta criada com sucesso!',
                                  24))

                    self.removeButton(self.create_account_button)
                elif queryCode == -1:
                    text_field_width = 500
                    text_field_height = 50
                    self.addTextField(
                        TextField(math.floor(WIN_WIDTH / 2 - text_field_width / 2),
                                  self.password_text.y + self.password_text.h + 50,
                                  text_field_width, text_field_height, WHITE, WARNING_COLOR, 'Usuario/Email em uso!',
                                  24))
                else:
                    text_field_width = 500
                    text_field_height = 50
                    self.addTextField(
                        TextField(math.floor(WIN_WIDTH / 2 - text_field_width / 2), self.password_text.y + self.password_text.h + 50,
                                  text_field_width, text_field_height, WHITE, WARNING_COLOR, 'Impossivel criar conta!', 24))


            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.game.running = False

                if event.type == pygame.KEYDOWN:
                    pressed = pygame.key.get_pressed()
                    key_text_value = str(event.unicode)

                    # Will notify all text fields that an input has been received.
                    self.notifyTextFieldsKeydownEvent(pressed, key_text_value)


class ConnectionOptionScreen(Screen):
    def __init__(self, game):
        # Initialize super class
        super().__init__(game)

        button_width = 350
        button_height = 50
        space_between = 40
        x_alignment = math.floor(WIN_WIDTH / 2) - math.floor(button_width / 2)
        y_alignment = math.floor(WIN_HEIGHT / 2) - math.floor((3 / 2) * button_height + space_between)
        self.op1_button = self.addButton(
            Button(x_alignment, y_alignment, button_width, button_height, WHITE, BLACK, 'Entrada Automatica',
                   32))
        self.op2_button = self.addButton(
            Button(x_alignment, y_alignment + button_height + space_between, button_width, button_height,
                   WHITE, BLACK, 'Criar Sala', 32))
        self.op3_button = self.addButton(
            Button(x_alignment, y_alignment + 2 * button_height + 2 * space_between, button_width,
                   button_height, WHITE, BLACK, 'Listar Salas', 32))
        self.return_button = self.addButton(Button(20, 20, 60, 30, WHITE, BLACK, 'ret', 32))

    def draw(self):
        self.running = True
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.game.running = False

            self.game.screen.blit(self.game.intro_background, (0, 0))
            self.blitAllElements()
            self.game.clock.tick(FRAMERATE)
            pygame.display.update()

            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()

            if self.op1_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                self.game.roomOp = 0

                roomID = self.game.client.requestAutoJoin(self.game.myPlayer.playerIdInServer)
                if roomID != -1:
                    self.game.myPlayer.setRoom(roomID)
                    self.running = False
                else:
                    print("Nao foi possivel efetuar o autojoin")

            if self.op2_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                self.game.roomOp = 1
                self.navigator.gotoScreen(RoomScreen(self.game))
                self.running = False

            if self.op3_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                self.game.roomOp = 2
                self.navigator.gotoScreen(ChooseRoomScreen(self.game))
                self.running = False

            if self.return_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                self.navigator.returnScreen()
                self.running = False


class RoomScreen(Screen):
    def __init__(self, game):
        # Initialize super class
        super().__init__(game)

        text_field_width = 300
        text_field_height = 50
        x_alignment = math.floor(WIN_WIDTH / 2) - math.floor(text_field_width / 2)
        y_alignment = math.floor(WIN_HEIGHT / 2) - math.floor(text_field_height / 2) - 200

        # Buttons
        self.return_button = self.addButton(Button(20, 20, 60, 30, WHITE, BLACK, 'ret', 32))
        self.create_room_button = self.addButton(
            Button(y_alignment + 200, x_alignment, 300, 50, WHITE, BLACK, 'Criar', 32))

        # Text Fields
        self.room_name_text = self.addTextField(
            TextField(x_alignment, y_alignment, text_field_width, text_field_height, BLACK, WHITE, 'Nome', 24))
        y_alignment += math.floor(3 * text_field_height / 2)
        self.room_password_text = self.addTextField(
            TextField(x_alignment, y_alignment, text_field_width, text_field_height, BLACK, WHITE, 'Senha', 24))

    def draw(self):
        self.running = True
        while self.running:

            self.game.screen.blit(self.game.intro_background, (0, 0))
            self.blitAllElements()
            self.game.clock.tick(FRAMERATE)
            pygame.display.update()

            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()

            if self.return_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                self.navigator.returnScreen()
                self.running = False

            if self.create_room_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                created = self.game.client.createServerRoom(self.room_name_text.content,
                                                            self.room_password_text.content, self.game.room_capacity)
                print("created: ", created)
                print(type(created))
                if created:
                    roomID = self.game.client.joinSpecificRoom(self.room_name_text.content,
                                                               self.room_password_text.content,
                                                               self.game.myPlayer.playerIdInServer)
                    if roomID != -1:
                        self.game.myPlayer.setRoom(roomID)
                        self.game.roomOp = 1
                        self.game.room_name = self.room_name_text.content
                        self.game.room_password = self.room_password_text.content
                        print("Room name: ", self.game.room_name)
                        print("Room password: ", self.game.room_password)
                        self.running = False
                    else:
                        print("Erro ao entrar na sala.")
                else:
                    print("Erro ao criar a sala")
                    text_field_width = 250
                    text_field_height = 50
                    self.addTextField(
                        TextField(self.room_name_text.x + self.room_name_text.w + 20, self.room_name_text.y,
                                  text_field_width, text_field_height, WHITE, WARNING_COLOR, 'Nome em uso', 24))

            # Tests if room_name_text is in typing mode (also testing and handling if the text field is clicked)
            self.updateTextFieldsTypingController(mouse_pos, mouse_pressed)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.game.running = False

                if event.type == pygame.KEYDOWN:
                    pressed = pygame.key.get_pressed()
                    key_text_value = str(event.unicode)

                    # Will notify all text fields that an input has been received.
                    self.notifyTextFieldsKeydownEvent(pressed, key_text_value)


class ChooseRoomScreen(Screen):
    def __init__(self, game):
        # Initialize super class
        super().__init__(game)

        # Buttons
        self.return_button = self.addButton(Button(20, 20, 60, 35, WHITE, BLACK, 'ret', 32))
        self.update_rooms = self.addButton(Button(100, WIN_HEIGHT - 150, 150, 35, WHITE, BLACK, 'update', 32))
        self.prev_rooms = self.addButton(Button(WIN_WIDTH - 450, WIN_HEIGHT - 150, 150, 35, WHITE, BLACK, 'prev', 32))
        self.next_rooms = self.addButton(Button(WIN_WIDTH - 250, WIN_HEIGHT - 150, 150, 35, WHITE, BLACK, 'next', 32))

        self.page_index = 0
        self.items_per_page = 5

        # Keeps room list data received from server query
        self.room_list = []
        # Keeps button elements that are being rendered at screen
        self.room_elements = []

        self.updateRooms()
        self.drawRooms()

    def draw(self):
        self.running = True
        while self.running:
            self.validateButtonsState()
            self.game.screen.blit(self.game.intro_background, (0, 0))
            self.blitAllElements()
            self.game.clock.tick(FRAMERATE)
            pygame.display.update()

            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()

            if self.return_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                self.navigator.returnScreen()
                self.running = False

            if self.update_rooms.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                self.updateRooms()
                self.drawRooms()

            if self.prev_rooms.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                if self.page_index > 0:
                    self.page_index -= 1
                    self.drawRooms()

            if self.next_rooms.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                if not self.isLastPage():
                    self.page_index += 1
                    self.drawRooms()

            self.handleRoomChoice(mouse_pos, mouse_pressed)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.game.running = False

    def handleRoomChoice(self, mouse_pos, mouse_pressed):
        for elements in self.room_elements:
            for index, element in enumerate(elements):
                if element.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                    if index == 0:
                        self.navigator.gotoScreen(InputRoomPassword(self.game, element.content))
                        self.running = False

    def validateButtonsState(self):
        if self.page_index == 0:
            if self.elementExists(self.prev_rooms, self.buttons):
                self.removeButton(self.prev_rooms)
        else:
            if not self.elementExists(self.prev_rooms, self.buttons):
                self.addButton(self.prev_rooms)

        if self.isLastPage():
            if self.elementExists(self.next_rooms, self.buttons):
                self.removeButton(self.next_rooms)
        else:
            if not self.elementExists(self.next_rooms, self.buttons):
                self.addButton(self.next_rooms)

    def isLastPage(self):
        return not len(self.room_list) > (1 + self.page_index) * self.items_per_page

    def updateRooms(self):
        self.room_list = self.game.client.requestAllRooms()
        self.page_index = 0
        print(self.room_list)

    def drawRooms(self):
        self.deleteAllTextFields()

        text_field_width = math.floor(WIN_WIDTH * 1 / 5)
        text_field_height = 50
        x_alignment = math.floor(WIN_WIDTH / 1 / 5) - math.floor(text_field_width / 2)
        y_alignment = math.floor(WIN_HEIGHT / 4)

        self.room_elements = []
        for index, room in enumerate(self.room_list):
            if self.page_index * self.items_per_page <= index < (self.page_index + 1) * self.items_per_page:
                field1 = self.addTextField(
                    TextField(x_alignment, y_alignment, text_field_width, text_field_height, BLACK, WHITE, str(room[0]),
                              24))
                x_alignment += text_field_width
                field2 = self.addTextField(
                    TextField(x_alignment, y_alignment, text_field_width, text_field_height, BLACK, WHITE, str(room[1]),
                              24))
                x_alignment += text_field_width
                field3 = self.addTextField(
                    TextField(x_alignment, y_alignment, text_field_width, text_field_height, BLACK, WHITE, str(room[2]),
                              24))
                x_alignment += text_field_width
                field4 = self.addTextField(
                    TextField(x_alignment, y_alignment, text_field_width, text_field_height, BLACK, WHITE, str(room[3]),
                              24))
                y_alignment += text_field_height + 30
                x_alignment = math.floor(WIN_WIDTH / 1 / 5) - math.floor(text_field_width / 2)

                # Saves elements to be processed when clicked
                self.room_elements.append([field1, field2, field3, field4])


class InputRoomPassword(Screen):
    def __init__(self, game, room_name):
        # Initialize super class
        super().__init__(game)

        self.room_name = room_name

        # Text Fields
        self.password = self.addTextField(
            TextField(math.floor(WIN_WIDTH / 2 - 150), math.floor(WIN_HEIGHT * 1 / 3), 300, 50, BLACK, WHITE, 'Senha',
                      24))

        # Buttons
        self.return_button = self.addButton(Button(20, 20, 60, 35, WHITE, BLACK, 'ret', 32))
        self.submit_login_button = self.addButton(
            Button(math.floor(WIN_WIDTH / 2 - 150 / 2), self.password.y + self.password.h + 40, 150, 35, WHITE, BLACK,
                   'Entrar', 32))

    def draw(self):
        self.running = True
        while self.running:
            self.game.screen.blit(self.game.intro_background, (0, 0))
            self.blitAllElements()
            self.game.clock.tick(FRAMERATE)
            pygame.display.update()

            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()

            if self.return_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                self.navigator.returnScreen()
                self.running = False

            if self.submit_login_button.clickSequenceAnalyze(mouse_pos, mouse_pressed):
                roomID = self.game.client.joinSpecificRoom(self.room_name,
                                                           self.password.content,
                                                           self.game.myPlayer.playerIdInServer)
                if roomID != -1:
                    self.game.myPlayer.setRoom(roomID)
                    self.game.roomOp = 2
                    self.game.room_name = self.room_name
                    self.game.room_password = self.password.content
                    print("Room name: ", self.game.room_name)
                    print("Room password: ", self.game.room_password)
                    self.running = False
                else:
                    text_field_width = 250
                    text_field_height = 50
                    self.addTextField(
                        TextField(self.password.x + self.password.w + 20, self.password.y,
                                  text_field_width, text_field_height, WHITE, WARNING_COLOR, 'Senha incorreta!', 24))

            # Tests if room_name_text is in typing mode (also testing and handling if the text field is clicked)
            self.updateTextFieldsTypingController(mouse_pos, mouse_pressed)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.game.running = False

                if event.type == pygame.KEYDOWN:
                    pressed = pygame.key.get_pressed()
                    key_text_value = str(event.unicode)

                    # Will notify all text fields that an input has been received.
                    self.notifyTextFieldsKeydownEvent(pressed, key_text_value)


class Stack:
    def __init__(self):
        self.stack = []
        self.top_index = -1

    def push(self, element):
        self.stack.append(element)
        self.top_index += 1

    def pop(self):
        if len(self.stack) > 1:
            popped = self.stack.pop()
            self.top_index -= 1
            return popped
        return None

    def top(self):
        return self.stack[self.top_index]


if __name__ == '__main__':
    game = Game()
    game.new()
    game.introScreen()
    game.establishConnection()
    while game.running:
        game.runEngine()
    game.gameOver()

    pygame.quit()
    sys.exit()
