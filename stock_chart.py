import pyqtgraph as pg
import numpy as np

class DateAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        # Ensure this method takes only 3 arguments
        return super().tickStrings(values, scale, spacing)

class InvertedViewBox(pg.ViewBox):
    """A custom ViewBox that inverts horizontal mouse drag movement"""
    
    def mouseDragEvent(self, ev, axis=None):
        # If this is a horizontal drag
        if axis == 0 or axis is None:
            # Invert the direction of horizontal movement by creating a new event
            # with inverted horizontal position delta
            if ev.isFinish():
                pos = ev.lastPos()
                dif = pos - ev.buttonDownPos()
                # Create modified position with inverted x
                modif_pos = ev.buttonDownPos() + pg.Point(-dif.x(), dif.y())
                
                # Create a modified event
                modif_ev = ev.copy()
                modif_ev._lastPos = modif_pos
                
                # Pass the modified event to parent class
                super().mouseDragEvent(modif_ev, axis)
            else:
                # For ongoing drags, invert the delta x
                pos = ev.pos()
                dif = pos - ev.lastPos()
                # Create modified position with inverted x movement
                modif_pos = ev.lastPos() + pg.Point(-dif.x(), dif.y())
                
                # Create a modified event
                modif_ev = ev.copy()
                modif_ev._pos = modif_pos
                
                # Pass the modified event to parent class
                super().mouseDragEvent(modif_ev, axis)
        else:
            # Vertical drags are unchanged
            super().mouseDragEvent(ev, axis)

class StockChart(pg.PlotWidget):
    def __init__(self, parent=None):
        # Create a custom ViewBox with inverted horizontal movement
        viewbox = InvertedViewBox()
        
        # Create a custom DateAxis for x-axis
        date_axis = DateAxis(orientation='bottom')
        
        # Create plot with custom ViewBox
        super().__init__(parent=parent, viewBox=viewbox, axisItems={'bottom': date_axis})
        
        # Set background color and other properties
        self.setBackground('k')
        self.showGrid(x=True, y=True)
        self.getAxis("left").setPen(pg.mkPen('w'))
        self.getAxis("bottom").setPen(pg.mkPen('w'))
        
        # Initialize empty plots
        self.line_plot = None
        self.candle_plot = None
        self.volume_plot = None
        
        # Set up a custom viewport margin for better readability
        self.getViewBox().setDefaultPadding(0.05)
