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
import select


REQ_PLAYERS = 2
TIME_LIMIT = 3
TIMER_ACTIVE = True

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



# class Client:
#   def __init__(self, connection, address):
#     self.connection = connection
#     self.address = address
#     self.host, self.port = address
#     self.name = '{}:{}'.format(host, port)

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

# class Message:
#   global client_data
#   global connected_idnums
#   global live_idnums

#   def __init__(self, receiver, subject, msg):
#     self.receiver = receiver
#     self.subject = subject
#     self.msg = msg

#   def forward(self):
#     for rec_idnum in self.receiver:
#       client_data[rec_idnum]["connection"].send(message)



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
    #is threading necessary here?
    #it just registers the client then halts
    thread = threading.Thread(target=client_handler, args=(idnum, connection, client_address), daemon=True)
    thread_list.append(thread)
    thread.start()


def client_handler(idnum, connection, address):
  """Runs from new thread; registers new client in lists and informs others of connection; updates view if game in progress"""
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
  prev_tile = []

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
  "prev_tile" : prev_tile
  }

  #send welcome message
  connection.send(tiles.MessageWelcome(idnum).pack())

  # inform other clients of this one
  for idnum_receiver in connected_idnums:
          client_data[idnum_receiver]["connection"].send(tiles.MessagePlayerJoined(client_data[idnum]["name"], idnum).pack()) 
          client_data[idnum]["connection"].send(tiles.MessagePlayerJoined(client_data[idnum_receiver]["name"], idnum_receiver).pack())
  # add to list of connected
  connected_idnums.append(idnum)

  #Tier4: update here to inform new conection of current game
  if game_in_progress == True:

    # notify client  of players who started current game
    for idnums in game_start_idnums:
      client_data[idnum]["connection"].send(tiles.MessagePlayerTurn(idnums).pack())

    # notify client of players eliminated from current game
    for idnums in game_start_idnums:
      if idnums not in live_idnums:
        client_data[idnum]["connection"].send(tiles.MessagePlayerEliminated(idnums).pack())

    # notify client of all tiles/tokens already on board
    for turn in turn_log:
      client_data[idnum]["connection"].send(turn.pack())

    # notify client real current turn
    client_data[idnum]["connection"].send(tiles.MessagePlayerTurn(turn_idnum).pack())

    # thread closes upon completion
    # client now exists as entity registered to main process


def check_start_conditions():
  """run from main processs, checks global conditions to start a game"""
  while game_in_progress == False:
    if (len(connected_idnums) >= REQ_PLAYERS):
      for idnums in connected_idnums:
        try:
          client_data[idnums]["connection"].send(tiles.MessageCountdown().pack())
        except:
          connected_idnums.remove(idnums)
          continue

      time.sleep(1)
      setup_game()
      print('Starting game...')
      time.sleep(1)
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
    client_data[idnums]["connection"].send(tiles.MessageGameStart().pack())

  # distribute first tiles to players
  for idnums in live_idnums:
    for _ in range(tiles.HAND_SIZE):
      tileid = tiles.get_random_tileid()
      client_data[idnums]["connection"].send(tiles.MessageAddTileToHand(tileid).pack())
      #update player's hand list
      client_data[idnums]["hand"].append(tileid)
    print('client {} hand: {}'.format(idnums, client_data[idnums]["hand"]))



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
    client_data[idnums]["connection"].send(tiles.MessagePlayerTurn(turn_idnum).pack())
  #move timer for first turn  
  if TIMER_ACTIVE == True:
    threading.Thread(target=move_timer, daemon=True).start()

  buffer = bytearray()
  
  # Enter infinte loop for receiving chunks
  while True:
    print('current turn is:', turn_idnum)

    #clear buffer
    # print('buffer before clear={}'.format(len(buffer)))
    # buffer = buffer[:]
    # print('buffer after clear={}'.format(len(buffer)))

    # ignore messages if its not the players turn
    chunk = client_data[turn_idnum]["connection"].recv(4096)
    print('data received from {}'.format(turn_idnum))

    # not chunk represents signal of disconnection from server
    if not chunk:

      print('client {} disconnected'.format(client_data[turn_idnum]["address"]))
      discon_idnum = turn_idnum

      # notify all connected the player has been eliminated
      for idnums in connected_idnums:
        if idnums != discon_idnum:
          try:
            client_data[idnums]["connection"].send(tiles.MessagePlayerEliminated(discon_idnum).pack())
          except:
            print('player {} could not be informed that {} has been eliminated'.format(idnums, discon_idnum))

      # notify all connected the player has left
      for idnums in connected_idnums:
        if idnums != discon_idnum:
          try:
            client_data[idnums]["connection"].send(tiles.MessagePlayerLeft(discon_idnum).pack())
          except:
            print('player {} could not be informed that {} has left the game'.format(idnums, discon_idnum))

      #remove player from game
      try:
        live_idnums.remove(turn_idnum)
      except:
        print('discon_idnum {} not found in live_idnums'.format(discon_idnum))

      # remove player from connections list
      try:
        connected_idnums.remove(discon_idnum)
      except:
        print('discon_idnum {} not found in connected_idnums'.format(connected_idnums))

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

      print('received message {}'.format(msg))

      # sent by the player to put a tile onto the board (all turns except second)
      if isinstance(msg, tiles.MessagePlaceTile):
        #print('MessagePlaceTile:{}{}{}{}{}'.format(msg.x, msg.y, msg.tileid, msg.rotation, msg.idnum))
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
      try:
        client_data[idnums]["connection"].send(msg.pack())
      except:
        #observing player disconnected; remove from connected_idnums
        print('missing connection removed')
        connected_idnums.remove(idnums)
        continue

    turn_log.append(msg)
    update_and_notify()

    #update hand
    client_data[turn_idnum]["hand"].remove(msg.tileid)
    print('tile {} removed from {}s hand'.format(msg.tileid, turn_idnum))

    # issue replacement tile to active player
    tileid = tiles.get_random_tileid()
    client_data[turn_idnum]["connection"].send(tiles.MessageAddTileToHand(tileid).pack())

    #update hand
    client_data[turn_idnum]["hand"].append(tileid)
    print('tile {} added to {}s hand'.format(tileid, turn_idnum))
    print('{}s hand: {}'.format(turn_idnum, client_data[turn_idnum]["hand"]))

    #update moves_played counter
    client_data[turn_idnum]["moves_played"] += 1
    progress_turn()

  # sent by the player in the second turn, to choose their token's starting path
  elif isinstance(msg, tiles.MessageMoveToken):
    
    #this doesnt seem to be required???!?!?!??
    for idnums in connected_idnums:
      try:
        client_data[idnums]["connection"].send(msg.pack())
        print('token update sent to {}'.format(idnums))
      except:
        #observing player disconnected; remove from connected_idnums
        print('missing connection removed')
        connected_idnums.remove(idnums)
        continue

    turn_log.append(msg)
    update_and_notify()
    #update moves_played counter
    client_data[turn_idnum]["moves_played"] += 1
    progress_turn()


def update_and_notify():
  global client_data
  global board
  global live_idnums
  global eliminated

  prev_eliminated = copy.deepcopy(eliminated)
  positionupdates, eliminated = board.do_player_movement(live_idnums)

  print('eliminated:{}'.format(eliminated))

  # notify all clients of new token positions on board
  # n.b. this was previously after elimination check
  for idnums in connected_idnums:
      for msg in positionupdates:
        try:
          turn_log.append(msg)
          client_data[idnums]["connection"].send(msg.pack())
        except:
          #should never be reached as eliminated players are removed before this
          print('player {} could not be informed of position updates'.format(idnums))
          continue
          #connected_idnums.remove(idnums)


  # notify all clients of eliminated players
  if len(eliminated) > 0:
      # check for eliminated not in prev eliminated
      for elim in eliminated:
        if elim not in prev_eliminated:
          # remove from live_idnums
          live_idnums.remove(elim)
          # all connected to be notified
          for idnums in connected_idnums:
            try:
              client_data[idnums]["connection"].send(tiles.MessagePlayerEliminated(elim).pack())
            except:
              # this likly is not connected due to mulitple eliminations in the same turn
              # this player will be removed when the eliminated list reaches them
              print('player {} could not be informed of the elimination of {}'.format(idnums, elim))
              continue



  # check if a player has won the game
  if (len(live_idnums)) == 1:
    print('live_idnums: {}'.format(live_idnums))
    print('connected_idnums: {}'.format(connected_idnums))
    game_over()


def progress_turn():
  #determine whos turn it is
  global TIMER_ACTIVE
  global live_idnums
  global turn_idnum # players will be notified this player can make next turn
  global buffer

  # print('before turn progression:')
  # print('turn_idnum: ', turn_idnum )
  # print('live_idnums: ', live_idnums)

  # progress the order & nominate next turn_idnum
  if turn_idnum in live_idnums:
    turn_idnum = live_idnums.pop(0)
    live_idnums.append(turn_idnum)
    turn_idnum = live_idnums[0]
  else:
    #in case last player eliminated self
    # print(live_idnums)
    turn_idnum = live_idnums[0]

  # print('after turn progression:')
  # print('turn_idnum: ', turn_idnum )
  # print('live_idnums: ', live_idnums)

  # Announce to every client it is this players turn
  for idnums in connected_idnums:
    try:
      client_data[idnums]["connection"].send(tiles.MessagePlayerTurn(turn_idnum).pack())
      print('players notified of new turn')
    except:
      connected_idnums.remove(idnums)
  
  #initiate timer
  if TIMER_ACTIVE == True:
    move_thread = threading.Thread(target=move_timer, daemon=True)
    move_thread.start()


# if a player doesnt make a valid move within TIMER_LIMIT seconds, the server makes a move for them
def move_timer():
  """ Runs in new thread based on turn; Makes a valid move for the player after TIMER_LIMIT seconds """
  global turn_idnum
  print('move timer started for {}'.format(turn_idnum))
  tracked_idnum = turn_idnum
  time_start = time.perf_counter()
  global TIME_LIMIT

  while True:
    time_now = time.perf_counter()
    if (time_now-time_start)>TIME_LIMIT:
      print('times up!')
      force_move()
      break
    if tracked_idnum != turn_idnum:
      print('move played!')
      break
  print('leaving timer...')

def force_move():
  """Runs in move_timer thread based on turn; determines the move to be forced"""
  print('forced move starting')
  global turn_idnum
  global board
  global turn_log
  global client_data

  random.seed(time.time())
  check = False
  checkcount = 0

  #detect move type needed: tile or token
  # player_turncount = 0
  # for log_msg in turn_log:
  #   if log_msg.idnum == turn_idnum:
  #     player_turncount += 1
  #print('moves_played:', client_data[turn_idnum]["moves_played"])

  while check == False:
    if client_data[turn_idnum]["moves_played"] == 1:
    # if player_turncount == 1:
    # if board.have_player_position(turn_idnum):
        print('inside token loop')
        # should be the location of the first tile
        x = client_data[turn_idnum]["prev_tile"][0]
        y = client_data[turn_idnum]["prev_tile"][1]
        position = random.randrange(0, 8)
        checkcount += 1
        check = board.set_player_start_position(turn_idnum, x, y, position)

        print(turn_idnum, x, y, position)
        time.sleep(1)
        random.seed(time.time())
    else: 
    # tile placement required
        print('inside tile loop')
        x = random.randrange(0, 5)
        y = random.randrange(0, 5)
        tileid = client_data[turn_idnum]["hand"][random.randrange(0,4)]
        rotation = random.randrange(0, 4)
        checkcount += 1
        client_data[turn_idnum]["prev_tile"] = [x, y]
        check = board.set_tile(x, y, tileid, rotation, turn_idnum)

  print('move has been forced')
  print('checkcount = {}'.format(checkcount))
  #print('player_turncount = {}'.format(player_turncount))
  #need to convert above into a msg
  if client_data[turn_idnum]["moves_played"] == 1:
    msg = tiles.MessageMoveToken(turn_idnum, x, y, position)
  else:
    msg = tiles.MessagePlaceTile(turn_idnum, tileid, rotation, x, y)

  #sends message for processing
  process_msg(msg)


def game_over():
  print('GAME OVER')
  time.sleep(1)
  # reset all global variables related to game
  reset_game_state()
  check_start_conditions()

def reset_game_state():
  """Resets global game variables and enables new game to start"""
  global live_idnums
  global board
  global turn_idnum
  global game_in_progress
  global turn_log

  #clear hands from any players in previous game
  for idnums in game_start_idnums:
    if idnums in connected_idnums:
      client_data[idnums]["hand"].clear()
      client_data[idnums]["moves_played"] = 0


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
#threading.Thread(target=check_start_conditions).start()