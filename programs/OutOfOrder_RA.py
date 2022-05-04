from context import *

roles = {'self': ('localhost', 5000), 'RB': ('localhost', 5001), 'RC': ('localhost', 5002),}

ch = Channel(Label["LOOP", Recv[int, 'RB', Recv[int, 'RC', "LOOP"]]], roles)

while True:
    a = ch.recv()
    print(a)
    b = ch.recv()
    print(b)