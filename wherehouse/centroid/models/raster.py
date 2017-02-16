"""A raster object for efficiently computing point in polygon."""
import numpy


class Raster(object):
    """A class for manipulating raster files."""

    grid = None
    nrows = None
    ncols = None
    cellsize = None
    lonmin = None
    latmin = None

    def load_data_from_file(self, fname):
        """Load raster data from a file.

        TODO: Find the format name.
        """
        fid = open(fname, 'r')

        self.ncols = int(fid.readline().split()[1])
        self.nrows = int(fid.readline().split()[1])
        self.lonmin = float(fid.readline().split()[1])
        self.latmin = float(fid.readline().split()[1])
        self.cellsize = float(fid.readline().split()[1])

        grid = []
        for Line in fid:
            line = Line.rstrip().split()
            grid.append([int(k) for k in line])

        self.grid = numpy.array(grid)

    def in_poly(self, lon, lat):
        """Lookup the raster value for the cell containing a lat, lon pair."""
        j = int((lon - self.lonmin) / self.cellsize)
        i = self.nrows - int((lat - self.latmin) / self.cellsize)
        if (i >= 0) and (i < self.nrows) and (j >= 0) and (j < self.ncols):
            return self.grid[i, j]
        else:
            return 0

    def in_poly_vec(self, lon, lat):
        """Lookup the raster value for multiple lat lon pairs."""
        j = ((lon - self.lonmin) / self.cellsize).astype(int)
        i = self.nrows - ((lat - self.latmin) / self.cellsize).astype(int)

        idx = numpy.intersect1d(
            numpy.where(((i >= 0) & (i < self.nrows)))[0],
            numpy.where(((j >= 0) & (j < self.ncols)))[0]
        )

        vals = numpy.zeros(len(lon))
        vals[idx] = self.grid[i[idx], j[idx]]

        return vals.astype(int)

    def get_x(self, lon):
        """Return the x index of the raster correpsonding to a lon value."""
        return int((lon - self.lonmin) / self.cellsize)

    def get_y(self, lat):
        """Return the y index of the raster correpsonding to a lat value."""
        return self.nrows - int((lat - self.latmin) / self.cellsize)

    def unique_values(self):
        """Return a list of all the unique raster values."""
        return numpy.unique(self.grid)
