import server
import client
import threading

list = []
server0 = threading.Thread(target=server)
list.append(server0)
player1 = threading.Thread(target=client)
list.append(player1)
player2 = threading.Thread(target=client)
list.append(player2)
player3 = threading.Thread(target=client)
list.append(player3)
player4 = threading.Thread(target=client)
list.append(player4)

print('Auto-starting 4 player game')

for x in list:
    print('starting {}'.format(x))
    x.start()


