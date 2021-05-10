import socket
import sys
import tiles
import socket
import sys
import tiles
import threading
import queue
import time
import random

# I deliberately left out some things that's stored by Player/Server class as to not mess up your own logic
# So don't be surprise if the Player/Server class will need to store more things

class Player():
# stores id
# stores name
# stores connection
# stores address
# stores move
  pass

class Server():
# stores list of CLIENTS
# stores board
# stores players is/was participating in the game
# stores live_idnums
# stores queue 
# lock = threading.Lock() # Needed for certain situation where to prevent race condition, CAN BE IGNORED  
                          # ONLY NEEDED THIS ONCE IN MY CODE DON"T THINK TOO MUCH ABOUT IT
  pass

  def listen_for_new_clients():
    # While true loop to constantly listen for new clients
    pass

  def thread_listen():
    # thread = thread(target=listen_for_new_clients)
    # thread start
    pass

  # IMPORTANT QUEUE LOGIC

  def process_queue_items():
    # While True loop
    # queue item = queue.get()
    # function = queue item[0]
    # parameter = queue item[1]
    # if there is a parameter DO function(parameter)
    # IF there is no parameter DO function()
    pass

def queue_thread():
  # thread = thread(target=process_queue_items)
  # thread start
  pass

# The idea of the queue is that a thread is constantly getting items from the queue and halt the main thread until all items has been completed 

def ask_for_tile(self, Player):
  # chunk = Player.connection.recv()
  # msg = tiles.read( chunk ) USE tiles functions to read messages
  # if msg is valid:
  # Player.move = msg
  #
  # IMPORTANT
  # queue.task_done() THIS NOTIFIES THE queue.join() THAT THE TASK IS DONE AND YOU CAN STOP BLOCKING
  pass

def run_game(self):
  # queue_put wait_for_clients()
  # queue.join()

  # broadcast all the players that has joined
  
  # welcome all the players that joined

  # send game starting message to players

  # give players their starting hand tiles

  # live_idnums = player's ID in PLAYERS LIST, NOT CLIENTS LIST

  # while( live_id_nums > 2 ):
  # current player = ???? implement your own logic here 
  # broadcast current player's turn to all CLIENTS

  # queue.put( (ask_for_tile, (current_player)) )
  # queue.join BLOCKS UNTIL ask_for_tile HAS COMPLETED ITS EXECUTION

  # move = current_player.move
  # process this VALID move
  # broadcast the move to ALL CLIENTS

  # positionupdates, eliminated = self.board.do_player_movement(self.live_idnums)
  # broadcast position updates and eliminated players

  # this player's turn is over, increment something to go to next player

  pass
  
  # If game is over, reset player information that needs to be resetted
  # reset board information and some other things
  # ^ outside of while loop but still in run_game function





###############################################################################################################################################################
server = Server()
server.thread_listen()
server.queue_thread()

while True:
  server.run_game()
