# Fast Loop
Version: 0.0.9 Alpha
**This document is a WIP**

## What is Fast Loop?
Fast loop makes inserting new loops easy. With the ability to preview the loop(s) before actually inserting them, you dont need to worry about making adjustments afterwards.
There are two modes for inserting loops:
* Single: Insert a single loop.  
<img src="https://github.com/Jrome90/Fast-Loop-Images/blob/main/Demo_Single.gif" width="256" height="256">  

* Mutli Loop: Insert two or more loops.
<img src="https://github.com/Jrome90/Fast-Loop-Images/blob/main/Demo_Multi.gif" width="256" height="256"> 

Activate single mode by pressing 1 on the keyboard or multi loop mode by pressing 2-9 on the keyboard.
You can also increase the number of loops by pressing = or numpdad+, or decrease with - or numpad-.

In addition to the two modes to insert loops, there are sub modes that can be used together with those modes:
* Midpoint: Insert the loops at midpoint of the edge the mouse is near.  
<img src="https://github.com/Jrome90/Fast-Loop-Images/blob/main/Demo_Midpoint.gif" width="256" height="256">  

* Perpendicular: The inserted loop is perpendicular to the edge that the mouse is near.  
<img src="https://github.com/Jrome90/Fast-Loop-Images/blob/main/Demo_Perpendicular.gif" width="256" height="256">  

* Mirror: Mirror the loops across the midpoint of the edge mouse is near.  
<img src="https://github.com/Jrome90/Fast-Loop-Images/blob/main/Demo_Mirrored.gif" width="256" height="256">  

Toggle the abilty to change the scale(spacing) of the loops when using multi loop mode with the W key.


#### Snapping ####
* Enable snap points to snap the loop to evenly spaced points along the edge.  
* Lock the points to prevent them from moving when a loop is inserted, allowing you to add additional loops with the same spacing along the edge.
Locking also keeps it from moving when hovering over different edges.

* When snap divisions is set to one, use the factor slider to set a custom percentage to snap to. You can press F to invert the value to flip to the other side.

Fast loop isn't just for inserting loops. You can alter exising loops by sliding them around or removing them too.    
* To slide the selected loop or edge(s) press and hold alt to invoke the edge slide operator and then click and drag.   
 <img src="https://github.com/Jrome90/Fast-Loop-Images/blob/main/Demo_Edge_Slide.gif" width="256" height="256"> 
 
  * holding ctrl while pressing alt makes the loop even depending on what side it's on  
  <img src="https://github.com/Jrome90/Fast-Loop-Images/blob/main/Demo_Edge_Slide_Ctrl.gif" width="256" height="256"> 
  
  * holding shift while pressing alt tries to preserve the loop's shape  
  <img src="https://github.com/Jrome90/Fast-Loop-Images/blob/main/Demo_Edge_Slide_Shift.gif" width="256" height="256">  
  
  When you are done release alt.  
  
Switch to Select Loop mode to select an edge loop.  
Remove loops by switching to Remove Loop mode.

### New in 0.0.9  
**Position Override**  
Position Override give you more control over where each loop is placed.  
When inserting just one, or multiple loops (up to 9) you can "override" the position of each loop.  
There are two interpolation types to choose from: Percentage and distance.  
To activate Position Override click on the "Position Override" button located in the active tool panel (when using the active tool version) or in the N panel under the edit tab.  
Read more information about this feature [Here](https://github.com/Jrome90/Fast-Loop/wiki/Position-Override)


## What is Fast Loop Classic?
Fast Loop Classic is a trimmed down version of Fast Loop.
* Click to insert a loop.
* shift+mouse click to insert a loop with flow
* ctrl+mouse click to select a loop
* ctrl+shift+mouse click to remove a loop
* To slide the selected loop or edge(s) press and hold alt to invoke the edge slide operator and then click and drag. 
  * holding ctrl while pressing alt makes the loop even depending on what side it's on 
  * holding shift while pressing alt tries to preserve the loop's shape
  
 ### Edge Slide
The operator that both versions of fast loop use can also be a standalone operator.
Read more about the operator [Here](https://github.com/Jrome90/Fast-Loop/wiki/Edge-Slide-Operator)  

 
## Install:
* Download the zip file from github.
* Open Blender.
* Edit -> Preferences -> Click Install button and choose the zip file you downloaded.
* Click the Add-ons button on the left and then activate the addon by ticking the checkbox.

# To use:
## Fast Loop
* Click on either Fast Loop Classic or Fast Loop Toolbar button to activate the active tool version.
* Alternatively, use the shortcut keys: insert or alt+insert for Fast Loop Classic and Fast Loop operators respectively. 

## Edge Slide Operator
* Use the shortcut alt+`

See the help tab under preferences for each operators hotkeys.

# Notes
There are some slight differences in how Fast Loop and Fast Loop Classic are used.  
 
Right click is used to open the pie menu, there is a button in the top right to exit the operator. When using the active tool you can just change to a different tool to exit instead.
      
  # Requires the Edge Flow addon which can be found here:
https://github.com/BenjaminSauder/EdgeFlow
