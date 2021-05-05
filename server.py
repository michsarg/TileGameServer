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
disconnected_idnums = []
turn_order = [] # clients in this round & their order
client_data = {}
board = tiles.Board()
turn_idnum = 0
game_in_progress = False
eliminated = []
player_count = 0


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

  host, port = address
  name = '{}:{}'.format(host, port)

  idnum = player_count
  player_count += 1
  connected_idnums.append(idnum)
  
  client_data[idnum] = {
  "connection" : connection,
  "address" : address,
  "host" : host,
  "port" : port,
  "name" : name
  }

  # inform other players of this one

  for idnum_receiver in connected_idnums:
        if idnum_receiver != idnum:
          client_data[idnum_receiver]["connection"].send(tiles.MessagePlayerJoined(client_data[idnum]["name"], idnum).pack()) 

  # send welcome message
  connection.send(tiles.MessageWelcome(idnum).pack())

  # inform this player of others
  for idnum_receiver in connected_idnums:
    if idnum_receiver != idnum:
      client_data[idnum]["connection"].send(tiles.MessagePlayerJoined(client_data[idnum_receiver]["name"], idnum_receiver).pack())


def check_start_conditions():

  while game_in_progress == False:
    if (len(connected_idnums) >= REQ_PLAYERS):
      setup_game()
      run_game()



def setup_game():
  global turn_order
  global live_idnums
  global connected_idnums
  global game_in_progress
  game_in_progress = True

  #select players to add to game
  turn_order = copy.deepcopy(connected_idnums)
  print('turn order after connected copy: {}'.format(turn_order))
  random.shuffle(turn_order)
  print('turn order after shuffle: {}'.format(turn_order))
  while len(turn_order) > REQ_PLAYERS:
    turn_order.pop()
  print('turn order after crop: {}'.format(turn_order))
  live_idnums = copy.deepcopy(turn_order)
  print('live idnums after copy turn order: {}'.format(live_idnums))

  #populate live_idnums




  print('play order: {}'.format(turn_order))

  # MOVED BACKWARDS TO CLIENT HANDLER
  # send joining message
  # for idnum_sent in live_idnums:
  #   for idnum_receiver in connected_idnums:
  #     if idnum_sent != idnum_receiver:
  #       idnum = idnum_sent
  #       name = client_data[idnum_sent]["name"]
  #       client_data[idnum_receiver]["connection"].send(tiles.MessagePlayerJoined(name, idnum).pack())

  # sent start message
  for idnums in connected_idnums:
    client_data[idnums]["connection"].send(tiles.MessageGameStart().pack())

  # distribute first tiles to players
  for idnums in live_idnums:
    print('sending tiles')
    for _ in range(tiles.HAND_SIZE):
      tileid = tiles.get_random_tileid()
      client_data[idnums]["connection"].send(tiles.MessageAddTileToHand(tileid).pack())


def run_game():
  global board
  global turn_order
  global turn_idnum

  #start the first turn
  turn_idnum = turn_order[0]
  for idnums in connected_idnums:
    client_data[idnums]["connection"].send(tiles.MessagePlayerTurn(turn_idnum).pack())

  buffer = bytearray()

  # Enter infinte loop for processing received chunks
  while True:

    # ignore messages if its not the players turn
    for idnums in connected_idnums:
      if idnums == turn_idnum:
        chunk = client_data[idnums]["connection"].recv(4096)
        print('data received from {}'.format(idnums))
        if not chunk:
          print('client {} disconnected'.format(client_data[idnums]["address"]))
          return

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
  global eliminated
  global live_idnums

  prev_eliminated = copy.deepcopy(eliminated)
  positionupdates, eliminated = board.do_player_movement(live_idnums)

  # notify all clients of new token positions on board
  for idnums in connected_idnums:
    for msg in positionupdates:
      client_data[idnums]["connection"].send(msg.pack())

  # notify all clients of eliminated players
  if len(eliminated) > 0:
      # check for eliminated not in prev eliminated
      for elim in eliminated:
        if elim not in prev_eliminated:
          # all connected to be notified
          for idnums in connected_idnums:
            client_data[idnums]["connection"].send(tiles.MessagePlayerEliminated(elim).pack())

  # check if a player has won the game
  if (len(turn_order)-len(eliminated)) == 1:
    game_over()


def progress_turn():
  #determine whos turn it is
  global live_idnums
  global turn_idnum # players will be notified this player can make next turn
  global turn_order # includes all players; those elimated are still in here
  global eliminated

  # this will successfully progress the game, skipping elim players in turn order
  for index in range(len(turn_order)):
    # find the index that matches turn_idnum
    if turn_order[index] == turn_idnum:
      if (turn_order[(index+1)%len(turn_order)] not in eliminated \
        and turn_order[(index+1)%len(turn_order)] not in disconnected_idnums):
          turn_idnum = turn_order[(index+1)%len(turn_order)]
          break
      elif (turn_order[(index+2)%len(turn_order)] not in eliminated \
        and turn_order[(index+2)%len(turn_order)] not in disconnected_idnums):
        turn_idnum = turn_order[(index+2)%len(turn_order)]
        break
      elif (turn_order[(index+3)%len(turn_order)] not in eliminated \
        and turn_order[(index+3)%len(turn_order)] not in disconnected_idnums):
          turn_idnum = turn_order[(index+3)%len(turn_order)]
          break
      elif (turn_order[(index+4)%len(turn_order)] not in eliminated \
        and turn_order[(index+4)%len(turn_order)] not in disconnected_idnums):
          turn_idnum = turn_order[(index+4)%len(turn_order)]
          break

  for idnums in connected_idnums:
    # Announce to every client it is this players turn
    client_data[idnums]["connection"].send(tiles.MessagePlayerTurn(turn_idnum).pack())


def game_over():
  print('GAME OVER BROS')
  time.sleep(5)
  # reset all global variables related to game
  reset_game_state()
  check_start_conditions()

def reset_game_state():
  global live_idnums
  global turn_order
  global eliminated
  global board
  global turn_idnum
  global game_in_progress

  live_idnums.clear()
  turn_order.clear()
  eliminated.clear()
  turn_idnum = 0
  board.reset()
  game_in_progress = False

def check_connections():
  global connected_idnums
  global client_data
  global sock
  global disconnected_idnums
  sock_list = []
  print('check connections starting')

  while True:
    time.sleep(1)
    # print('checking connections')
    #READY TO READ RETURNS A LIST OF CLOSED IDNUMS
    if len(connected_idnums) > 0:
      
      sock_list = []

      for idnum in connected_idnums:
        sock_list.append(client_data[idnum]["connection"])

      ready_to_read, ready_to_write, in_error = \
        select.select(sock_list, sock_list, [])

      # convert disconnected names to disconnected idnums
      for discon_name in ready_to_read:
        discon_peer = discon_name.getpeername()
        discon_port = discon_peer[1]
        for idnums in connected_idnums:
          if discon_port == client_data[idnums]["port"]:
            #remove this discon_idnum from all relevant lists
            print('undiscon discon idnum found: {}'.format(idnums))
            remove_discon_idnum(idnums)

      ready_to_read.clear()
      ready_to_write.clear()


def remove_discon_idnum(discon_idnum):
  global live_idnums
  global connected_idnums
  #global turn_order
  global client_data
  #turn_idnum = 0
  global eliminated
  global disconnected_idnums

  for idnums in connected_idnums:
    client_data[idnums]["connection"].send(tiles.MessagePlayerLeft(discon_idnum).pack())
  
  if discon_idnum in live_idnums:
    live_idnums.remove(discon_idnum)
  
  if discon_idnum in connected_idnums:
    connected_idnums.remove(discon_idnum)
  
  disconnected_idnums.append(discon_idnum)
  print('{} disconnected'.format(discon_idnum))

  # if discon_idnum in client_data:

  # if discon_idnum in eliminated:


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('', 30020)
sock.bind(server_address)
threading.Thread(target=listen).start()
threading.Thread(target=check_start_conditions).start()
threading.Thread(target=check_connections).start()