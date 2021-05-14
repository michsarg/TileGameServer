# CITS3002 2021 Assignment
# Michael Sargeant 22737938

import socket
import tiles
import random
import copy
import time
import threading
import logging

PLAYER_LIMIT = 3

AUTO_RESTART = True
RESTART_WAIT = 3

AUTO_PLAY = True
TIME_LIMIT = 10


class Game_State:
  def __init__(self):
    """holds shared variables required for running the current game"""
    self.live_idnums = []
    self.connected_idnums = []
    self.eliminated = []
    self.client_data = {}
    self.board = tiles.Board()
    self.turn_idnum = -1
    self.game_in_progress = False
    self.player_count = 0
    self.buffer = bytearray()
    self.game_start_idnums = []
    self.turn_log = []
    logging.debug("game state created")


#LESS IMPORTANT TO GET CLIENT INTO CLASS BECAUSE ITS ALREADY IN DICTIONARY
# class Client:
#   def __init__(self, connection, address):
#     self.connection = connection
#     self.address = address
#     self.host, self.port = self.address
#     self.name = '{}:{}'.format(self.host, self.port)
#     self.hand = []
#     self.moves_played = 0
#     self.prev_tile_x = -1
#     self.prev_tile_y = -1

class Message:
  """handles a message to be transmitted to detect disconnected reciptients"""
  global game
  # global client_data

  def __init__(self, receiver, data):
    self.receiver = receiver
    self.data = data

  def transmit(self):
    """sends a message or removes the recipient client if they are disconnected"""
    try:
        game.client_data[self.receiver]["connection"].send(self.data)
    except:
      threading.Thread(target=remove_client, args=(self.receiver)).start()


def remove_client(discon_idnum):
  """fully removes an uncontactable/quit client from the game state"""
  global game

  lock = threading.Lock()
  lock.acquire()
  logging.debug('Acquired a lock')

  if discon_idnum in game.live_idnums:
    game.live_idnums.remove(discon_idnum)
    
    # notify all connected the player has been eliminated & left
    for idnums in game.connected_idnums:
      if idnums != discon_idnum:
        Message(idnums, tiles.MessagePlayerEliminated(discon_idnum).pack()).transmit()
        Message(idnums, tiles.MessagePlayerLeft(discon_idnum).pack()).transmit()
  
  game.connected_idnums.remove(discon_idnum)
  game.client_data.pop(discon_idnum)

  if discon_idnum == game.turn_idnum:
    progress_turn()
  
  logging.debug('Released a lock')
  lock.release()


def listen():
  """Runs from new thread; listens for new clients attempting to connect"""
  global game
  print('listening on {}'.format(sock.getsockname()))
  sock.listen(5)

  while True:
    connection, client_address = sock.accept()
    print('received connection from {}'.format(client_address))
    idnum = game.player_count
    game.player_count += 1
    #threading prevents corruption of main thread when player connects
    threading.Thread(target=client_handler, args=(idnum, connection, client_address), daemon=True).start()


def client_handler(idnum, connection, address):
  """Runs from new thread; registers new client in lists and informs others of connection, updates view if game in progress"""
  lock = threading.Lock()
  lock.acquire()
  logging.debug('Acquired a lock')

  global game

  host, port = address
  name = '{}:{}'.format(host, port)
  hand = []
  moves_played = 0
  prev_tile_x = -1
  prev_tile_y = -1
  timed_play = False

  idnum = game.player_count
  game.player_count += 1

  game.client_data[idnum] = {
  "connection" : connection,
  "address" : address,
  "host" : host,
  "port" : port,
  "name" : name,
  "hand" : hand,
  "moves_played" : moves_played,
  "prev_tile_x" : prev_tile_x,
  "prev_tile_y" : prev_tile_y,
  "timed_play" : timed_play
  }

  logging.debug('Released a lock')
  lock.release()

  #send welcome message & inform this client of others and others of this
  Message(idnum, (tiles.MessageWelcome(idnum).pack())).transmit()
  for idnum_receiver in game.connected_idnums:
          Message(idnum_receiver, tiles.MessagePlayerJoined(game.client_data[idnum]["name"], idnum).pack()).transmit()
          Message(idnum, tiles.MessagePlayerJoined(game.client_data[idnum_receiver]["name"], idnum_receiver).pack()).transmit()

  # add to list of connected
  game.connected_idnums.append(idnum)

  # Inform new connection of progress of current game
  if game.game_in_progress == True:

    # notify client of players who started current game
    for idnums in game.game_start_idnums:
      Message(idnum, tiles.MessagePlayerTurn(idnums).pack()).transmit()

    # notify client of players eliminated from current game
    for idnums in game.game_start_idnums:
      if idnums not in game.live_idnums:
        Message(idnum, tiles.MessagePlayerEliminated(idnums).pack()).transmit()

    # notify client of all tiles/tokens already on board
    for turn in game.turn_log:
      Message(idnum, turn.pack()).transmit()

    # notify client real current turn
    Message(idnum, tiles.MessagePlayerTurn(game.turn_idnum).pack()).transmit()


def check_start_conditions():
  """run from main processs, checks global conditions to start a game"""
  global game

  while game.game_in_progress == False:
    if (len(game.connected_idnums) >= PLAYER_LIMIT):
      for idnums in game.connected_idnums:
        Message(idnums, tiles.MessageCountdown().pack()).transmit()
      setup_game()
      print('Starting game...')
      run_game()


def setup_game():
  """run from main process, sets up game"""
  global game
  game.game_in_progress = True

  #select players to add to game & create live_idnums, game_start_idnums
  game.live_idnums = copy.deepcopy(game.connected_idnums)
  random.shuffle(game.live_idnums)
  while len(game.live_idnums) > PLAYER_LIMIT:
    game.live_idnums.pop(len(game.live_idnums)-1)
  game.game_start_idnums = copy.deepcopy(game.live_idnums)

  # sent start message
  for idnums in game.connected_idnums:
    Message(idnums, tiles.MessageGameStart().pack()).transmit()

  # distribute first tiles to players
  for idnums in game.live_idnums:
    for _ in range(tiles.HAND_SIZE):
      tileid = tiles.get_random_tileid()
      Message(idnums, tiles.MessageAddTileToHand(tileid).pack()).transmit()
      #update player's hand list
      game.client_data[idnums]["hand"].append(tileid)
    logging.debug('client {} hand: {}'.format(idnums, game.client_data[idnums]["hand"]))


def run_game():
  """Handles running of the game; runs in main process"""
 
  global game
  global AUTO_PLAY

  # initiate first turn outside of loop
  game.turn_idnum = game.live_idnums[0]
  for idnums in game.connected_idnums:
    Message(idnums, tiles.MessagePlayerTurn(game.turn_idnum).pack()).transmit()
  if AUTO_PLAY == True:
    threading.Thread(target=move_timer, daemon=True).start()

  game.buffer = bytearray()
  
  # Enter infinte loop for receiving chunks
  while True:

    # ignore messages if its not the players turn
    try:
      chunk = game.client_data[game.turn_idnum]["connection"].recv(4096)
    except:
      remove_client(game.turn_idnum)
      continue
    logging.debug('data received from {}'.format(game.turn_idnum))

    # not chunk represents disconnection
    if not chunk:
      logging.debug('client {} disconnected'.format(game.client_data[game.turn_idnum]["address"]))
      remove_client(game.turn_idnum)
      continue

    # extends the buffer with the chunk
    game.buffer.extend(chunk)

    #infinite loop for processing messages messages
    while True:
      #attempts to read and unpack a single message from the buffer array
      msg, consumed = tiles.read_message_from_bytearray(game.buffer)
      if not consumed:
        break

      #deletes everything before and including consumed:
      game.buffer = game.buffer[consumed:]

      logging.debug('received message {}'.format(msg))

      # sent by the player to put a tile onto the board (all turns except second)
      if isinstance(msg, tiles.MessagePlaceTile):
        if game.board.set_tile(msg.x, msg.y, msg.tileid, msg.rotation, msg.idnum):
          process_msg(msg)

      # sent by the player in the second turn, to choose their token's starting path
      elif isinstance(msg, tiles.MessageMoveToken):
        if not game.board.have_player_position(msg.idnum):
          if game.board.set_player_start_position(msg.idnum, msg.x, msg.y, msg.position):
            process_msg(msg)


def process_msg(msg):
  """detects whether message is place tile or place token and triggers game updates and progression"""
  global game

  # reset the timer variable if relevant
  if AUTO_PLAY == True:
    game.client_data[game.turn_idnum]["timed_play"] = False

  # sent by the player to put a tile onto the board (all turns except second)
  if isinstance(msg, tiles.MessagePlaceTile):

    # inform all clients of newly placed tile
    for idnums in game.connected_idnums:
      Message(idnums, msg.pack()).transmit()
    game.turn_log.append(msg)
    update_and_notify()

    #update prev_tile in case of play timeout next move
    game.client_data[game.turn_idnum]["prev_tile_x"] = msg.x
    game.client_data[game.turn_idnum]["prev_tile_y"] = msg.y

    # remove used tile from active player's hand
    game.client_data[game.turn_idnum]["hand"].remove(msg.tileid)

    # issue replacement tile to active player
    tileid = tiles.get_random_tileid()
    Message(game.turn_idnum, tiles.MessageAddTileToHand(tileid).pack()).transmit()

    #update hand
    game.client_data[game.turn_idnum]["hand"].append(tileid)

    #update moves_played counter
    game.client_data[game.turn_idnum]["moves_played"] += 1
    progress_turn()

  # sent by the player in the second turn, to choose their token's starting path
  elif isinstance(msg, tiles.MessageMoveToken):
    #inform all connected idnums of updated token positions
    for idnums in game.connected_idnums:
      Message(idnums, msg.pack()).transmit()

    game.turn_log.append(msg)
    update_and_notify()
    game.client_data[game.turn_idnum]["moves_played"] += 1
    progress_turn()


def update_and_notify():
  """updates board token positions and processes any consequent eliminations"""
  global game

  # retrieve updated game data
  positionupdates, game.eliminated = game.board.do_player_movement(game.live_idnums)
  logging.debug('eliminated:{}'.format(game.eliminated))

  # notify all clients of new token positions on board
  for msg in positionupdates:
    game.turn_log.append(msg)
    for idnums in game.connected_idnums:
        Message(idnums, msg.pack()).transmit()

  # Process eliminated players: different to disconnection, as player can remain observing
  if len(game.eliminated) > 0:
    # remove eliminated player from list of players, reset their game variables
    for elim in game.eliminated:
        game.live_idnums.remove(elim)
        game.client_data[elim]["hand"].clear
        game.client_data[elim]["moves_played"] = 0
        game.client_data[elim]["prev_tile_x"] = -1
        game.client_data[elim]["prev_tile_y"] = -1
        # inform connected idnums of elimination
        for idnums in game.connected_idnums:
          try:
            Message(idnums, tiles.MessagePlayerEliminated(elim).pack()).transmit()
          except:
            # left blank in case of multiple eliminations to be processed in this loop
            continue

  # check if a player has won the game
  if (len(game.live_idnums)) <= 1:
    logging.debug('live_idnums: {}'.format(game.live_idnums))
    logging.debug('connected_idnums: {}'.format(game.connected_idnums))
    game_over()


def progress_turn():
  #determine whos turn it is
  logging.debug("progress_turn called")
  global AUTO_PLAY
  global game

  # depends on receiving accurate live_idnum list
  if game.turn_idnum in game.live_idnums:
    game.turn_idnum = game.live_idnums.pop(0)
    game.live_idnums.append(game.turn_idnum)
    game.turn_idnum = game.live_idnums[0]
  else:
    game.turn_idnum = game.live_idnums[0]


  logging.debug("turn_idnum before progression:{}".format(game.turn_idnum))
  logging.debug("live_idnums:{}".format(game.live_idnums))

  # Announce to every client it is this players turn
  for idnums in game.connected_idnums:
    Message(idnums, tiles.MessagePlayerTurn(game.turn_idnum).pack()).transmit()

  #initiate play timeout timer
  if AUTO_PLAY == True:
    threading.Thread(target=move_timer, daemon=True).start()


def move_timer():
  """ Runs in new thread based on turn; Makes a valid move for the player after TIMER_LIMIT seconds """
  global TIME_LIMIT
  global game

  tracked_idnum = game.turn_idnum
  time_start = time.perf_counter()
  run_timer = True

  while run_timer == True:
    # cancel timer if move is made
    if tracked_idnum != game.turn_idnum:
      logging.debug('Forced move timer cancelled')
      run_timer = False
    time_now = time.perf_counter()
    if (time_now-time_start)>TIME_LIMIT:
      logging.debug('Times up! Forcing move...')
      force_move()
      run_timer = False


def force_move():
  """Runs in move_timer thread based on turn; determines the move to be forced"""
  logging.debug('forced move starting')
  global game

  random.seed(time.time())
  #check = False
  game.client_data[game.turn_idnum]["timed_play"] = True
  checkcount = 0

  logging.debug("moves played:{}".format(game.client_data[game.turn_idnum]["moves_played"]))

  #loop for randomly determining next move
  #while check == False:
  while game.client_data[game.turn_idnum]["timed_play"] == True:
    if game.game_in_progress == True:
      if game.client_data[game.turn_idnum]["moves_played"] == 1:
          x = game.client_data[game.turn_idnum]["prev_tile_x"]
          y = game.client_data[game.turn_idnum]["prev_tile_y"]
          position = random.randrange(0, 8)
          checkcount += 1
          # if valid move found, stop timer
          if game.board.set_player_start_position(game.turn_idnum, x, y, position) == True:
            game.client_data[game.turn_idnum]["timed_play"] = False
          random.seed(time.time())
      else:
          x = random.randrange(0, 5)
          y = random.randrange(0, 5)
          tileid = game.client_data[game.turn_idnum]["hand"][random.randrange(0,4)]
          rotation = random.randrange(0, 4)
          checkcount += 1
          # if valid move found, stop timer
          if game.board.set_tile(x, y, tileid, rotation, game.turn_idnum) == True:
            game.client_data[game.turn_idnum]["timed_play"] = False
    else:
      #stop loop if game is over
      check = False

  # final check if the game is still going and move hasnt been made
  if game.game_in_progress == True:
    logging.debug('move has been forced')
    if game.client_data[game.turn_idnum]["moves_played"] == 1:
      msg = tiles.MessageMoveToken(game.turn_idnum, x, y, position)
    else:
      msg = tiles.MessagePlaceTile(game.turn_idnum, tileid, rotation, x, y)
    process_msg(msg)



def game_over():
  """Resets game state on finish and initiates new round if applicable"""
  print('GAME OVER')
  reset_game_state()
  if AUTO_RESTART == True:
    time.sleep(RESTART_WAIT)
    check_start_conditions()


def reset_game_state():
  """Resets game state variables and enables new game to start"""
  global game

  #clear game records from any players in previous game
  for idnums in game.game_start_idnums:
    if idnums in game.connected_idnums:
      game.client_data[idnums]["hand"].clear()
      game.client_data[idnums]["moves_played"] = 0
      game.client_data[idnums]["prev_tile_x"] = -1
      game.client_data[idnums]["prev_tile_y"] = -1

  game.live_idnums.clear()
  game.turn_log.clear()
  game.turn_idnum = 0
  game.board.reset()
  game.game_in_progress = False


# Enable this option for extra commentry
logging.basicConfig(level=logging.DEBUG, format='(%(threadName)-9s) %(message)s',)

# Set up Server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('localhost', 30020)
sock.bind(server_address)
threading.Thread(target=listen).start()
game = Game_State()
check_start_conditions()