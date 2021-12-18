from channel import *
from sessiontype import *
from typechecking import verify_channels

@verify_channels
def main():
    #my_channel = Channel[Recv[int, Choose[Send[str, End], Recv[int, End]]]]()
    my_channel = Channel[Recv[int, Choose[Send[str, End], Choose[Send[int, End], Recv[int, End]]]]]()
    n = my_channel.recv()

    if n > 5:
        my_channel.choose(Branch.LEFT)
        my_channel.send("number was greater than 5")
    else:
        my_channel.choose(Branch.RIGHT)
        if n < 12:
            my_channel.choose(Branch.RIGHT)
            i = my_channel.recv()
        else:
            my_channel.choose(Branch.LEFT)
            my_channel.send(42)
        
if __name__ == '__main__':
    main()