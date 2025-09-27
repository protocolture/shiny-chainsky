## Note

This is probably easy to port to another board/platform etc however I have only built this to work with RasPi and wont be testing other platforms like Arduino that are commonly paired with electrical relays. Further, I selected this relay expansion board based
on my limited understanding of relays and amperage. I can offer no guarantees that this wont burn your house down, and I certainly
cannot guarantee that working with other hardware or a different OS wont burn your house down either. 


## Hardware Requirements

1. RasPi compatible with the waveshare board. I believe I am using a 3B
2. Raspberry Pi 8-ch Relay Expansion Board (https://www.waveshare.com/rpi-relay-board-b.htm)


## System Requirements

python
python3-pip
(pip install) RPi.GPIO


## Relay to GPIO Mapping

Channel label	29	P21	5	Channel 1
Channel label	31	P22	6	Channel 2
Channel label	33	P23	13	Channel 3
Channel label	36	P27	16	Channel 4
Channel label	35	P24	19	Channel 5
Channel label	38	P28	20	Channel 6
Channel label	40	P29	21	Channel 7
Channel label	37	P25	26	Channel 8
