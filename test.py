import server
import client_v2
import threading

print('ayyyy lmao')

list = []
server0 = threading.Thread(target=server)
list.append(server0)
player1 = threading.Thread(target=client_v2)
list.append(player1)
player2 = threading.Thread(target=client_v2)
list.append(player2)
player3 = threading.Thread(target=client_v2)
list.append(player3)
player4 = threading.Thread(target=client_v2)
list.append(player4)

print('ayyyy lmao')

for x in list:
    print('starting {}'.format(x))
    x.start()


