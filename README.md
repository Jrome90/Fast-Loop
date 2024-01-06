Shout-out to Hologram from the BA forums for feedback and taking time to test the addon.
Rename the addon folder to Fast Loop. If you don't blender will error when enabling.

## Fast Loop
**Added**  
* New sub mode to insert Vertices on edges.  
 <kbd>v</kbd> to enable.

* New sub mode to use selected edges to guide the loop's direction.  
 <kbd>a</kbd> to enable.

* UVs are now preserved after loop insertion.  
* Auto merge loops when auto merge is enabled.  

* Hold <kbd>ctrl</kbd> to snap the loop to either vertices, edges, or the midpoint of edges. (Uses blender snap settings for element types)

* <kbd>Shift</kbd>+ <kbd>Right click</kbd> to insert loops in the center.
  * Can be changed in addon preferences under keymaps tab.
 
* Numerical input used when scaling now works with more complicated input.  
 Some examples of the input that can be used:
  * 1m 2cm 3mm
  * 1.2m
  * 1 5/16m
  * 3cm's 2mms
  * 1ft 6in 100thou
  * 1' 6" 
  * 10p (where p is a replacement for %)

**Removed**    
* Select Loop (Ctrl + Click)
* Midpoint sub mode

**Fixed**  
* Loop preview updates correctly when increase/decrease loop count is mapped to the mouse wheel.
* Fixed issues when scene unit scale is anything other than one.
* Better support for industry compatible keymap. (Enable in the addon preferences)

#### UI/UX
**Added**  
* Draggable panel display in the viewport.
* Added a bar to display the distances between edges. 
  * Display settings can be changed using the HUD settings pop up menu.
  * The bar can be resized by clicking and dragging inside the little box to the right.

Fast Loop now works in 3d viewports other than the one the tool was invoked in. (Quad view not supported)

**Removed**  
* Operator panel in the N panel. 
* Pie menu
*Preference option to swap right and left click functionality. 
  * Should now be Synced with blender's "Select with Mouse Button" setting

#### Incremental Snapping:
**Added**  
* Option to use a distance value to set the space between snap points. 
  *  Tick the use distance checkbox and set a distance to use in the distance input field.
  * The Auto option calculates the number of segments to use, based on the distance used.
  * If use distance is enabled the following happens:
    *  Every 4th tick is major tick (Distances are only drawn near major ticks)
    *  The origin at which the snap points are calculated change sides based on the side the mouse is on.
       Lock the snap points <kbd>x</kbd> if you wish to prevent them from moving.
  * Toggle the center button to change the origin of the snap points to the center.

## Edge Slide  
#### UI/UX  
**Added**  
* Draggable panel display in the viewport.
* Highlight the edge closest to the mouse.

**Removed**  
* Integration of edge constrained translation. 
 * It's now its own operator.

## Edge Constrained Translation:
**How To Use**  
1. Select vertices then activate the operator.
2. Hover the mouse near a vertex. A representation of the axes of the current coordinate system will appear.
3. Press <kbd>X</kbd>(red), <kbd>Y</kbd>(green), or <kbd>Z</kbd>(blue) to select the corresponding axis to slide along.

**Added**  
* Hold <kbd>ctrl</kbd> to snap the postition to either vertices, edges, or the midpoint of edges. (Uses blender snap settings for element types)
  * Works with active and nearest snap settings

**Known Issues**  
*If you enable snapping, and then disable it by releasing <kbd>ctrl</kbd>, the position of the mouse and vertices' will most likely desync. This should not affect the useability.

### Requires the Edge Flow addon:
https://github.com/BenjaminSauder/EdgeFlow
