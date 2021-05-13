# CITS3002 2021 Assignment
#
# This file implements a basic server that allows a single client to play a
# single game with no other participants, and very little error checking.
#
# Any other clients that connect during this time will need to wait for the
# first client's game to complete.
#
# Your task will be to write a new server that adds all connected clients into
# a pool of players. When enough players are available (two or more), the server
# will create a game with a random sample of those players (no more than
# tiles.PLAYER_LIMIT players will be in any one game). Players will take turns
# in an order determined by the server, continuing until the game is finished
# (there are less than two players remaining). When the game is finished, if
# there are enough players available the server will start a new game with a
# new selection of clients.

import socket
import sys
import tiles
import random
import copy
import time
import threading
#import select
import logging

logging.basicConfig(level=logging.DEBUG, format='(%(threadName)-9s) %(message)s',)

REQ_PLAYERS = 3
TIME_LIMIT = 3
TIMER_ACTIVE = True
AUTO_RESTART = True

live_idnums = [] # list of players connected and in the game now
connected_idnums = [] # all connected players
eliminated = []
client_data = {}
board = tiles.Board()
turn_idnum = -1
game_in_progress = False
player_count = 0
buffer = bytearray()
thread_list = []
game_start_idnums = []
turn_log = []
first_tile_placed = []
player_tilechanges = 0



class Client:
  def __init__(self, connection, address):
    self.connection = connection
    self.address = address
    self.host, self.port = self.address
    self.name = '{}:{}'.format(self.host, self.port)

  # host, port = address
  # name = '{}:{}'.format(host, port)
  # hand = []
  # moves_played = 0
  # prev_tile = []

  # idnum = player_count
  # player_count += 1

  # client_data[idnum] = {
  # "connection" : connection,
  # "address" : address,
  # "host" : host,
  # "port" : port,
  # "name" : name,
  # "hand" : hand,
  # "moves_played" : moves_played,
  # "prev_tile" : prev_tile
  # }

# class Game:
#   def __init__():
#     self.board = tiles.Board()
#     self.live_idnums = []
#     self.connected_idnums = []
#     self.turn_idnum = 0
#     self.player_count = 0
#     self.game_in_progress = False

#   def add_player_to_game(player_idnum):
#     live_idnums.append(player_idnum)
  
#   def new_client_connected(connnection, address):
#     player_idnum = player_count
#     player_count += 1
#     connected_idnums.append(player_idnum)
#     player_idnum = Client(connection, address)
#     # inform new and existing clients of each other
#     for connected_clients in connected_idnums:
#         receiving_client.connection.send(tiles.MessagePlayerJoined(player_idnum.name, int(player_idnum)).pack()) 
#         player_idnum.connection.send(tiles.MessagePlayerJoined(connected_idnum.name, connected_idnum).pack())
#     # send welcome message
#     player_idnum.connection.send(tiles.MessageWelcome(player_idnum).pack())

class Message:
  global client_data
  global connected_idnums
  global live_idnums

  def __init__(self, receiver, data):
    self.receiver = receiver
    self.data = data

  def transmit(self):
    try:
        client_data[self.receiver]["connection"].send(self.data)
    except Exception as e:
      logging.debug(e)
      logging.debug('message could not send, removing', self.receiver)
      #needs a thread here and locking!
      removal_thread = threading.Thread(target=remove_client, args=(self.receiver))
      removal_thread.start()

def remove_client(discon_idnum):
  """fully removes an uncontactable/quit client from the game state"""
  
  # aquire lock
  lock = threading.Lock()
  lock.acquire()
  logging.debug('Acquired a lock')

  if discon_idnum in live_idnums:
    live_idnums.remove(discon_idnum)
    
    #BELOW NOTIFICATIONS MOVED INTO SAME LOOP
    
    # notify all connected the player has been eliminated
    # notify all connected the player has left
    for idnums in connected_idnums:
      if idnums != discon_idnum:
        Message(idnums, tiles.MessagePlayerEliminated(discon_idnum).pack()).transmit()
        Message(idnums, tiles.MessagePlayerLeft(discon_idnum).pack()).transmit()
  
  connected_idnums.remove(discon_idnum)
  #remove entry from client_data dictionary
  client_data.pop(discon_idnum)

  #release lock
  logging.debug('Released a lock')
  lock.release()


def listen():
  """Runs from new thread; listens for new clients attempting to connect"""
  global player_count
  global thread_list
  print('listening on {}'.format(sock.getsockname()))
  sock.listen(5)

  while True:
    connection, client_address = sock.accept()
    print('received connection from {}'.format(client_address))
    idnum = player_count
    player_count += 1
    #threading prevents interruption of main thread when player connects
    thread = threading.Thread(target=client_handler, args=(idnum, connection, client_address), daemon=True)
    thread_list.append(thread)
    thread.start()


def client_handler(idnum, connection, address):
  """Runs from new thread; registers new client in lists and informs others of connection; updates view if game in progress"""
  # aquire lock
  lock = threading.Lock()
  lock.acquire()
  logging.debug('Acquired a lock')

  global client_data
  global player_count
  global live_idnums
  global game_start_idnums
  global game_in_progress
  global tile_log

  host, port = address
  name = '{}:{}'.format(host, port)
  hand = []
  moves_played = 0
  prev_tile_x = -1
  prev_tile_y = -1

  idnum = player_count
  player_count += 1

  client_data[idnum] = {
  "connection" : connection,
  "address" : address,
  "host" : host,
  "port" : port,
  "name" : name,
  "hand" : hand,
  "moves_played" : moves_played,
  "prev_tile_x" : prev_tile_x,
  "prev_tile_y" : prev_tile_y
  }

  #release lock
  logging.debug('Released a lock')
  lock.release()

  #send welcome message
  Message(idnum, (tiles.MessageWelcome(idnum).pack())).transmit()

  # inform other clients of this one
  for idnum_receiver in connected_idnums:
          Message(idnum_receiver, tiles.MessagePlayerJoined(client_data[idnum]["name"], idnum).pack()).transmit()
          Message(idnum, tiles.MessagePlayerJoined(client_data[idnum_receiver]["name"], idnum_receiver).pack()).transmit()

  # add to list of connected
  connected_idnums.append(idnum)

  #Tier4: update here to inform new conection of current game
  if game_in_progress == True:

    # notify client  of players who started current game
    for idnums in game_start_idnums:
      Message(idnum, tiles.MessagePlayerTurn(idnums).pack()).transmit()

    # notify client of players eliminated from current game
    for idnums in game_start_idnums:
      if idnums not in live_idnums:
        Message(idnum, tiles.MessagePlayerEliminated(idnums).pack()).transmit()

    # notify client of all tiles/tokens already on board
    for turn in turn_log:
      Message(idnum, turn.pack()).transmit()

    # notify client real current turn
    Message(idnum, tiles.MessagePlayerTurn(turn_idnum).pack()).transmit()

    # thread closes upon completion
    # client now exists as entity registered to main process

def check_start_conditions():
  """run from main processs, checks global conditions to start a game"""
  while game_in_progress == False:
    if (len(connected_idnums) >= REQ_PLAYERS):
      for idnums in connected_idnums:
        Message(idnums, tiles.MessageCountdown().pack()).transmit()
      time.sleep(1)
      setup_game()
      print('Starting game...')
      #time.sleep(1)
      run_game()


def setup_game():
  """run from main process, sets up game"""
  global live_idnums
  global connected_idnums
  global game_start_idnums
  global game_in_progress
  game_in_progress = True

  #select players to add to game & create live_idnums, game_start_idnums
  live_idnums = copy.deepcopy(connected_idnums)
  random.shuffle(live_idnums)
  while len(live_idnums) > REQ_PLAYERS:
    live_idnums.pop(len(live_idnums)-1)
  game_start_idnums = copy.deepcopy(live_idnums)

  # sent start message
  for idnums in connected_idnums:
    Message(idnums, tiles.MessageGameStart().pack()).transmit()

  # distribute first tiles to players
  for idnums in live_idnums:
    for _ in range(tiles.HAND_SIZE):
      tileid = tiles.get_random_tileid()
      Message(idnums, tiles.MessageAddTileToHand(tileid).pack()).transmit()
      #update player's hand list
      client_data[idnums]["hand"].append(tileid)
    logging.debug('client {} hand: {}'.format(idnums, client_data[idnums]["hand"]))


def run_game():
  """run from main process, runs game"""
  global board
  global live_idnums
  global connected_idnums
  global turn_idnum
  global buffer
  global turn_log
  global TIMER_ACTIVE

  #start the first turn
  turn_idnum = live_idnums[0]
  for idnums in connected_idnums:
    Message(idnums, tiles.MessagePlayerTurn(turn_idnum).pack()).transmit()

  #move timer for first turn  
  if TIMER_ACTIVE == True:
    threading.Thread(target=move_timer, daemon=True).start()

  buffer = bytearray()
  
  # Enter infinte loop for receiving chunks
  while True:
    #logging.debug('current turn is:', turn_idnum)

    # ignore messages if its not the players turn
    chunk = client_data[turn_idnum]["connection"].recv(4096)
    logging.debug('data received from {}'.format(turn_idnum))

    # not chunk represents signal of disconnection from server
    if not chunk:

      logging.debug('client {} disconnected'.format(client_data[turn_idnum]["address"]))
            
      #notifications moved to remove_client method
      #remove player from game state
      # be careful here! yes, its right
      # the right thing to do here is treat a not chunk received the same as non-contactable disconnection
      remove_client(turn_idnum)

      # nothing more to do with disconnected player
      # choose who plays next and process their chunk
      progress_turn()
      continue

    # extends the buffer with the chunk
    buffer.extend(chunk)

    #infinite loop for processing messages messages
    while True:
      #attempts to read and unpack a single message from the buffer array
      msg, consumed = tiles.read_message_from_bytearray(buffer)
      if not consumed:
        break

      #deletes everything before and including consumed:
      buffer = buffer[consumed:]

      logging.debug('received message {}'.format(msg))

      # sent by the player to put a tile onto the board (all turns except second)
      if isinstance(msg, tiles.MessagePlaceTile):
        if board.set_tile(msg.x, msg.y, msg.tileid, msg.rotation, msg.idnum):
          process_msg(msg)

      # sent by the player in the second turn, to choose their token's starting path
      elif isinstance(msg, tiles.MessageMoveToken):
        if not board.have_player_position(msg.idnum):
          if board.set_player_start_position(msg.idnum, msg.x, msg.y, msg.position):
            process_msg(msg)


def process_msg(msg):
  """detects whether message is place tile or place token and triggers game updates and progression"""
  global client_data
  global connected_idnums
  global turn_log
  global board
  # sent by the player to put a tile onto the board (all turns except second)
  if isinstance(msg, tiles.MessagePlaceTile):

    # inform all clients of newly placed tile
    for idnums in connected_idnums:
      Message(idnums, msg.pack()).transmit()
    turn_log.append(msg)
    update_and_notify()

    #update prev_tile in case of play timeout next move
    try:
      client_data[turn_idnum]["prev_tile_x"] = msg.x
      client_data[turn_idnum]["prev_tile_y"] = msg.y
    except Exception:
      logging.debug("Could not access msg.x or msg.y")

    # remove used tile from active player's hand
    client_data[turn_idnum]["hand"].remove(msg.tileid)

    # issue replacement tile to active player
    tileid = tiles.get_random_tileid()
    Message(turn_idnum, tiles.MessageAddTileToHand(tileid).pack()).transmit()

    #update hand
    client_data[turn_idnum]["hand"].append(tileid)
    #print('tile {} added to {}s hand'.format(tileid, turn_idnum))
    #print('{}s hand: {}'.format(turn_idnum, client_data[turn_idnum]["hand"]))



    #update moves_played counter
    client_data[turn_idnum]["moves_played"] += 1
    progress_turn()

  # sent by the player in the second turn, to choose their token's starting path
  elif isinstance(msg, tiles.MessageMoveToken):
    #inform all connected idnums of updated token positions
    for idnums in connected_idnums:
      Message(idnums, msg.pack()).transmit()

    turn_log.append(msg)
    update_and_notify()
    client_data[turn_idnum]["moves_played"] += 1
    progress_turn()


def update_and_notify():
  """updates board token positions and processes any consequent eliminations"""
  global client_data
  global board
  global live_idnums
  global eliminated

  #prev_eliminated = copy.deepcopy(eliminated)
  positionupdates, eliminated = board.do_player_movement(live_idnums)

  logging.debug('eliminated:{}'.format(eliminated))

  # notify all clients of new token positions on board
  # n.b. this was previously after elimination check
  for msg in positionupdates:
    turn_log.append(msg) # N.B. this has been moved up so updates only recorded once
    for idnums in connected_idnums:
        Message(idnums, msg.pack()).transmit()

  # procces eliminated players
  # note: not the same process as a disconnection, as player remains in connected idnums
  if len(eliminated) > 0:
    # remove eliminated player from live_idnums and reset their game related variables
    for elim in eliminated:
        live_idnums.remove(elim)
        client_data[elim]["hand"].clear
        client_data[elim]["moves_played"] = 0
        client_data[elim]["prev_tile_x"] = -1
        client_data[elim]["prev_tile_y"] = -1
        # inform connected idnums of elimination
        for idnums in connected_idnums:
          try:
            Message(idnums, tiles.MessagePlayerEliminated(elim).pack()).transmit()
          except:
            # left blank in case of multiple eliminations to be processed in this loop
            continue

  # check if a player has won the game
  if (len(live_idnums)) <= 1:
    logging.debug('live_idnums: {}'.format(live_idnums))
    logging.debug('connected_idnums: {}'.format(connected_idnums))
    game_over()


def progress_turn():
  #determine whos turn it is
  global TIMER_ACTIVE
  global live_idnums
  global turn_idnum 

  # depends on receiving accurate live_idnum list
  turn_idnum = live_idnums.pop(0)
  live_idnums.append(turn_idnum)
  turn_idnum = live_idnums[0]

  # Announce to every client it is this players turn
  for idnums in connected_idnums:
    Message(idnums, tiles.MessagePlayerTurn(turn_idnum).pack()).transmit()

  #initiate timer
  if TIMER_ACTIVE == True:
    move_thread = threading.Thread(target=move_timer, daemon=True)
    move_thread.start()


# if a player doesnt make a valid move within TIMER_LIMIT seconds, the server makes a move for them
def move_timer():
  """ Runs in new thread based on turn; Makes a valid move for the player after TIMER_LIMIT seconds """
  global turn_idnum
  #logging.debug('move timer started for {}'.format(turn_idnum))
  tracked_idnum = turn_idnum
  time_start = time.perf_counter()
  global TIME_LIMIT

  while True:
    time_now = time.perf_counter()
    if (time_now-time_start)>TIME_LIMIT:
      #logging.debug('times up!')
      force_move()
      break
    if tracked_idnum != turn_idnum:
      #logging.dbug('move played!')
      break

def force_move():
  """Runs in move_timer thread based on turn; determines the move to be forced"""
  logging.debug('forced move starting')
  global turn_idnum
  global board
  global turn_log
  global client_data

  random.seed(time.time())
  check = False
  checkcount = 0

  #loop for randomly determining next move
  while check == False:
    if game_in_progress == True:
      if client_data[turn_idnum]["moves_played"] == 1:
          #logging.debug('inside token loop')
          x = client_data[turn_idnum]["prev_tile_x"]
          y = client_data[turn_idnum]["prev_tile_y"]
          position = random.randrange(0, 8)
          checkcount += 1
          check = board.set_player_start_position(turn_idnum, x, y, position)
          random.seed(time.time())
      else:
          #logging.debug('inside tile loop')
          x = random.randrange(0, 5)
          y = random.randrange(0, 5)
          tileid = client_data[turn_idnum]["hand"][random.randrange(0,4)]
          rotation = random.randrange(0, 4)
          checkcount += 1
          check = board.set_tile(x, y, tileid, rotation, turn_idnum)
    else:
      #stop if game is over
      check = False

  if game_in_progress == True:
    logging.debug('move has been forced')
    # logging.debug('checkcount = {}'.format(checkcount))
    if client_data[turn_idnum]["moves_played"] == 1:
      msg = tiles.MessageMoveToken(turn_idnum, x, y, position)
    else:
      msg = tiles.MessagePlaceTile(turn_idnum, tileid, rotation, x, y)
    process_msg(msg)


def game_over():
  print('GAME OVER')
  # reset all global variables related to game
  reset_game_state()
  if AUTO_RESTART == True:
    check_start_conditions()


def reset_game_state():
  """Resets global game variables and enables new game to start"""
  global live_idnums
  global board
  global turn_idnum
  global game_in_progress
  global turn_log

  #clear game records from any players in previous game
  for idnums in game_start_idnums:
    if idnums in connected_idnums:
      client_data[idnums]["hand"].clear()
      client_data[idnums]["moves_played"] = 0
      client_data[idnums]["prev_tile_x"] = -1
      client_data[idnums]["prev_tile_y"] = -1

  live_idnums.clear()
  turn_log.clear()
  turn_idnum = 0
  board.reset()
  game_in_progress = False


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('localhost', 30020)
sock.bind(server_address)
threading.Thread(target=listen).start()
check_start_conditions()