# lego-sorter

This is a project demo for the lego sorter at IoT Impact

To run this call 
  
   $ python3 lego-sorter.py
   
 You can also run the command with the follow options
 
whether or not the Raspberry Pi camera should be displayed
 "-s", "--showcamera", type=int, default=0
 
the framerate that the camera gets updated
"-f", "--framerate", type=int, default=30

resolution of camera
"-r", "--resolution", type=int, default=480

color to sort out (R, O, Y, G, B)
"-c", "--colour", type=int, default=0
