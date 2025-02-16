import pyqtgraph as pg

class DateAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        # Ensure this method takes only 3 arguments
        return super().tickStrings(values, scale, spacing)
