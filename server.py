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

REQ_PLAYERS = 4

live_idnums = [] # list of players connected and in the game now
connected_idnums = [] # all connected players
eliminated = []
client_data = {}
board = tiles.Board()
turn_idnum = -1
game_in_progress = False
player_count = 0

# class Client:
#   def __init__(connection, address):
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


def listen():
  print('listening on {}'.format(sock.getsockname()))
  sock.listen(5)
  while True:
    connection, client_address = sock.accept()
    print('received connection from {}'.format(client_address))
    client_handler(connection, client_address)


def client_handler(connection, address):
  global client_data
  global player_count
  global live_idnums

  host, port = address
  name = '{}:{}'.format(host, port)

  idnum = player_count
  player_count += 1

  client_data[idnum] = {
  "connection" : connection,
  "address" : address,
  "host" : host,
  "port" : port,
  "name" : name
  }

  # send welcome message
  connection.send(tiles.MessageWelcome(idnum).pack())
  # inform other clients of this one
  for idnum_receiver in connected_idnums:
          client_data[idnum_receiver]["connection"].send(tiles.MessagePlayerJoined(client_data[idnum]["name"], idnum).pack()) 
          client_data[idnum]["connection"].send(tiles.MessagePlayerJoined(client_data[idnum_receiver]["name"], idnum_receiver).pack())
  # add to list of connected
  connected_idnums.append(idnum)


def check_start_conditions():
  while game_in_progress == False:
    if (len(connected_idnums) >= REQ_PLAYERS):
      for idnums in connected_idnums:
        client_data[idnums]["connection"].send(tiles.MessageCountdown().pack())
      time.sleep(4)
      setup_game()
      time.sleep(1)
      run_game()


def setup_game():
  global live_idnums
  global connected_idnums
  global game_in_progress
  game_in_progress = True

  #select players to add to game & create live_idnums
  live_idnums = copy.deepcopy(connected_idnums)
  random.shuffle(live_idnums)
  while len(live_idnums) > REQ_PLAYERS:
    live_idnums.pop(len(live_idnums)-1)

  # sent start message
  for idnums in connected_idnums:
    client_data[idnums]["connection"].send(tiles.MessageGameStart().pack())

  # distribute first tiles to players
  for idnums in live_idnums:
    for _ in range(tiles.HAND_SIZE):
      tileid = tiles.get_random_tileid()
      client_data[idnums]["connection"].send(tiles.MessageAddTileToHand(tileid).pack())


def run_game():
  global board
  global live_idnums
  global connected_idnums
  global turn_idnum

  #start the first turn
  turn_idnum = live_idnums[0]
  for idnums in connected_idnums:
    client_data[idnums]["connection"].send(tiles.MessagePlayerTurn(turn_idnum).pack())

  buffer = bytearray()

  # Enter infinte loop for processing received chunks
  while True:
    print('current turn is:', turn_idnum)

    # ignore messages if its not the players turn
    chunk = client_data[turn_idnum]["connection"].recv(4096)
    print('data received from {}'.format(turn_idnum))
    if not chunk:
      print('client {} disconnected'.format(client_data[turn_idnum]["address"]))
      #this is how disconnections are received by the server
      live_idnums.remove(turn_idnum)
      for idnums in connected_idnums:
        #if idnums != turn_idnum:
        client_data[idnums]["connection"].send(tiles.MessagePlayerLeft(turn_idnum).pack())
          # needs elimination message?

      #disappearing code test
      #return

    buffer.extend(chunk)

    while True:
      msg, consumed = tiles.read_message_from_bytearray(buffer)
      if not consumed:
        break

      buffer = buffer[consumed:]

      print('received message {}'.format(msg))

      # sent by the player to put a tile onto the board (all turns except second)
      if isinstance(msg, tiles.MessagePlaceTile):
        if board.set_tile(msg.x, msg.y, msg.tileid, msg.rotation, msg.idnum):

          # inform all clients of newly placed tile
          for idnums in connected_idnums:
            client_data[idnums]["connection"].send(msg.pack())

          # update board and notify clients
          update_and_notify()

          # issue replacement tile to active player
          tileid = tiles.get_random_tileid()
          client_data[turn_idnum]["connection"].send(tiles.MessageAddTileToHand(tileid).pack())

          #initiate the next turn in the game
          progress_turn()

      # sent by the player in the second turn, to choose their token's starting path
      elif isinstance(msg, tiles.MessageMoveToken):
        if not board.have_player_position(msg.idnum):
          if board.set_player_start_position(msg.idnum, msg.x, msg.y, msg.position):
            
            # update board and notify clients
            update_and_notify()

            # start next turn
            progress_turn()


def update_and_notify():
  global client_data
  global board
  global live_idnums
  global eliminated

  prev_eliminated = copy.deepcopy(eliminated)
  positionupdates, eliminated = board.do_player_movement(live_idnums)

  print('eliminated:{}'.format(eliminated))

  # notify all clients of eliminated players
  if len(eliminated) > 0:
      # check for eliminated not in prev eliminated
      for elim in eliminated:
        if elim not in prev_eliminated:
          # remove from live_idnums
          live_idnums.remove(elim)
          # all connected to be notified
          for idnums in connected_idnums:
            client_data[idnums]["connection"].send(tiles.MessagePlayerEliminated(elim).pack())

  # notify all clients of new token positions on board
  for idnums in connected_idnums:
      for msg in positionupdates:
        client_data[idnums]["connection"].send(msg.pack())

  # check if a player has won the game
  if (len(live_idnums)) == 1:
    game_over()


def progress_turn():
  #determine whos turn it is
  global live_idnums
  global turn_idnum # players will be notified this player can make next turn

  print('before turn progression:')
  print('turn_idnum: ', turn_idnum )
  print('live_idnums: ', live_idnums)

  # progress the order & nominate next turn_idnum
  turn_idnum = live_idnums.pop(0)
  live_idnums.append(turn_idnum)
  turn_idnum = live_idnums[0]

  print('after turn progression:')
  print('turn_idnum: ', turn_idnum )
  print('live_idnums: ', live_idnums)

  # Announce to every client it is this players turn
  for idnums in connected_idnums:
    client_data[idnums]["connection"].send(tiles.MessagePlayerTurn(turn_idnum).pack())
  

def game_over():
  print('GAME OVER')
  time.sleep(5)
  # reset all global variables related to game
  reset_game_state()
  check_start_conditions()

def reset_game_state():
  global live_idnums
  global board
  global turn_idnum
  global game_in_progress

  live_idnums.clear()
  turn_idnum = 0
  board.reset()
  game_in_progress = False


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('', 30020)
sock.bind(server_address)
threading.Thread(target=listen).start()
threading.Thread(target=check_start_conditions).start()
# threading.Thread(target=check_connections).start()