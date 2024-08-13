# =======================================
# Imports
import numpy
import matplotlib
matplotlib.use('TKAgg')
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, CheckButtons
from scipy import stats
from nibabel.viewers import OrthoSlicer3D

import logging
logger = logging.getLogger(__name__)

# =======================================
# Constants

# =======================================
# Classes
class ScanViewer(OrthoSlicer3D):
    """ Custom built scan viewer
    
    ScanViewer piggybacks off the OrthoSlicer3D ultility provided with nibabel. 
    Some of the methods have been overriden to allow access to neccessary 
    functionality.
    
    The viewer expects a scan.NII class as its arg. From there it will pull the
    4D data out and pass it to the OrthoSlicer3D
    
    Examples
    --------
    >>> from input_deck import InputDeck
    >>> from scan import Scan
    >>> inp = InputDeck('example.inp')
    >>> pet = Scan(inp.cards['pet'][0])
    >>> pet.import_and_save_nii(os.getcwd())
    >>> viewer = ScanViewer(pet.scan)
    
    """
    def __init__(self, fdata, expected=None, scan_size=None, affine=None, axes=None, title='Scan Viewer'):
        """
        Parameters
        ----------
        fdata : array-like object; 3D or 4D
            The data to show, can be suvs or raw data
        expected : array-like object; 3D or 4D, optional
            The user can pass an expected scan to compare results for quality 
            control purposes.
        scan_size : array-like object; 3D
            Describes the size of the scan in measurable units, not indexes
        affine : array-like or None, optional
            Affine transform for the data. This is used to determine
            how the data should be sliced for plotting into the sagittal,
            coronal, and axial view axes. If None, identity is assumed.
            The aspect ratio of the data are inferred from the affine
            transform.
        axes : tuple of mpl.Axes or None, optional
            3 or 4 axes instances for the 3 slices plus volumes,
            or None (default).
        title : str or None, optional
            The title to display. Can be None (default) to display no
            title.
        """
        # get the averaged data and sset all values less than 0 to 0 for vizualization
        try:
            # average all the voxels over time
            self.averaged_data = numpy.mean(fdata, 3)
        except IndexError:
            # we will enter this flow when the user passes a 3D array
            self.averaged_data = fdata
        # remove all values less than 0 for vizualization
        self.averaged_data = self.averaged_data[(self.averaged_data > 0.)]
        
        fdata[fdata < 0.] = 0.

        # initialize the orthoslicer
        super().__init__(fdata, title=title)
        try:
            self.end_frame = self._data.shape[3]
        except IndexError:
            self.end_frame = 0
        self.scan_size = scan_size
        
        # initialize the expected data
        if expected is None:
            self.e_fdata = None
            self.e_averaged_data = None
        else:
            self.e_fdata = expected
            try:
                self.e_averaged_data = numpy.mean(expected, 3)
            except IndexError:
                self.e_averaged_data = expected
            # remove all values less than 0 for vizualization
            self.e_averaged_data = self.e_averaged_data[(self.e_averaged_data > 0.)]
        
                
        
    def build(self):
        """ Build the viewer to look like this:
           ^ +---------+   ^ +---------+  +---+
           | |         |   | |         |  |   |
             |   Sag   |     |   Cor   |  | c |
           S |    0    |   S |    1    |  | o |
             |         |     |         |  | l |
             +---------+     +---------+  | o |
                  A  -->     <--  R       | r |
           ^ +---------+     +---------+  | m |
           | |         |     |         |  | a |
             |  Axial  |     |   His   |  | p |
           A |    2    |     |    3    |  |   |
             |         |     |         |  |   |
             +---------+     +---------+  +---+
             <--  R          <-- suv -->       
            +-+ +------------------------------+
            |p| |        frame slider          |
            +-+ +------------------------------+
                 +-----+ +-----+ +-----+ +-----+
                 | com | | rld | | prt | | ext |
                 +-----+ +-----+ +-----+ +-----+
        """
        # move the subplot over to make room for the slider and color mapper
        self._plt.subplots_adjust(left=0.05, right=0.70, bottom=0.20)
        
        # if the user has given the scan size, adjust our slice windows to match
        if not self.scan_size is None:
            self.adjust_slice_aspect_ratios(self.scan_size)

        # change the colormapping
        self.cmap = 'jet'
        self.clim = (0., numpy.percentile(self.averaged_data, 99.))
        
        # build the slider
        slider_BB = [0.25, 0.10, 0.60, 0.05]
        self.sFrame = Slider(self._plt.axes(slider_BB, facecolor='green'), 
                             label='Frame', valmin=0., valmax=self.end_frame, 
                             valstep=1, valinit=0, valfmt="%1.0f")
        
        # build the play check box
        play_BB = [0.05, 0.10, 0.12, 0.05]
        self.cPlay = CheckButtons(self._plt.axes(play_BB), ['Play'], [False])
        self.cPlay.rectangles[0].set_width(0.125)
        self.cPlay.rectangles[0].set_height(0.30)

        # build the buttons
        button_size = [0.07, 0.05]
        self.bCompare = create_button([0.40, 0.02]+button_size, 'Compare')
        self.bReload = create_button([0.50, 0.02]+button_size, 'Reload')
        self.bPrint = create_button([0.60, 0.02]+button_size, 'Print')
        self.bExit = create_button([0.70, 0.02]+button_size, 'Exit')
        
        # build the colorbar
        cbar_BB = [0.75, 0.25, 0.10, 0.65]
        self.cbLegend = self._plt.colorbar(self._ims[0], cax=self._plt.axes(cbar_BB))
        
        # set the widget functions
        self.sFrame.on_changed(self._slider_update)
        self.cPlay.on_clicked(self._play_clicked)
        self.comp_cid=self.bCompare.on_clicked(self._compare_clicked)
        self.bPrint.on_clicked(self._print_clicked)
        self.bExit.on_clicked(self._exit_clicked)
        
    def adjust_slice_aspect_ratios(self, scan_size):
        # change the aspect ratio of the im plots
        for ax, coords in zip(self._axes[:3], ((0, 2), (1, 2), (0, 1))):
            ax.set_adjustable('box')
            ar = (self._data.shape[coords[0]]/self._data.shape[coords[1]]) * (scan_size[coords[1]]/scan_size[coords[0]])
            ax.set_aspect(ar)

    
    def reset_viewer(self):
        if self.end_frame>0:
            self.sFrame.val = int(self.end_frame/2)
            self._set_volume_index(int(self.end_frame/2), update_slices=True)
        
        self._set_position(*[i/2. for i in self._data.shape[:3]], notify=True)
        
    def plot_histogram(self, log=True, numOfBins=100):
        # remove the OrthoSlicer3D volume plot, we will replace this with our histogram plot
        if self.end_frame==0:
            for fig in self._figs:
                x = self._axes[1].get_position().x0
                w = self._axes[1].get_position().width
                y = self._axes[2].get_position().y0
                h = self._axes[2].get_position().height
                self._axes.append(fig.add_axes(self._plt.axes([x, y, w, h])))
                
        ax = self._axes[3]
        ax.cla()
        ax.set_title('Averaged Data')

        # create the histogram
        bins = create_bins(numOfBins, [numpy.percentile(self.averaged_data, 1.), numpy.percentile(self.averaged_data, 99.)], log=log)
        bin_h, bin_boundary = numpy.histogram(self.averaged_data, bins)
        bin_w = bin_boundary[1]-bin_boundary[0]
        bin_h = bin_h/float(numpy.max(bin_h))

        ax.bar(bin_boundary[:-1], bin_h, width=numpy.diff(bin_boundary), align='edge')
        try: # if the user provided an expected scan use it
            # create a kernel smoothed density function to describe the expected behavior
            kde = stats.gaussian_kde(self.e_averaged_data)
            min_x, max_x = numpy.percentile(self.e_averaged_data, 1.), numpy.percentile(self.e_averaged_data, 99.)
            x = create_bins(numOfBins, [min_x, max_x], log=log)
            p = kde(x)
            p /= numpy.max(p)
            ax.plot(x, p, 'y') # plot the kde in yellow
            
            # set the view of the plot window to be relative to the expected value
            ax.set_xlim(0.0, max_x*1.02)
            ax.set_ylim(0, 1.05)

        # This will enter this exception if self.expected_data is None
        except ValueError:
            # if no expected scan is present, use the histogram to define the window
            ax.set_xlim(-self.clim[1]*0.02, self.clim[1]*1.02)
            ax.set_ylim(0, 1.05)
            
            self.bCompare.disconnect(self.comp_cid)
            self.bCompare.ax.visible = False
        
        # change the scale of the x axis
        if log:
            ax.set_xscale('log', basex=numpy.e)
        
    def _slider_update(self, val):
        # set the slider value equal to the frame number and upate the canvas
        self._set_volume_index(self.sFrame.val, update_slices=True)

    def _play_clicked(self, *arg):
        frame = self.sFrame.val
        while self.cPlay.get_status()[0]:
            self._plt.pause(1.)
            if frame<self.end_frame:
                frame += 1
            else:
                frame = 0
            self.sFrame.set_val(frame)
            self._set_volume_index(frame, update_slices=True)
    
    def _print_clicked(self, *arg):
        self._plt.savefig('fig.png')
        
    def _compare_clicked(self, *arg):
        viewer = ScanViewer(self.e_scan)
        viewer.build()
        viewer._plt.show()

    def _exit_clicked(self, *arg):
        self._plt.close('all')

    def show(self):
        """Override the OrthoSlicer3D show method... Show the slicer in 
        blocking mode; convenience for ``plt.show()``
        """
        self._plt.show(block=False)

    def _draw(self):
        """ Override the OrthoSlicer's draw method to remove the volume plot 
        and replace with our own... Update all four (or three) plots
        """
        if self._closed:  # make sure we don't draw when we shouldn't
            return
        for ii in range(3):
            ax = self._axes[ii]
            ax.draw_artist(self._ims[ii])
            if self._cross:
                for line in self._crosshairs[ii].values():
                    ax.draw_artist(line)
            ax.figure.canvas.blit(ax.bbox)
        
        
# =======================================
# Functions
def create_button(BB, label=None, color='lightgrey', hovercolor='grey'):
    return Button(plt.axes(BB), label=label, color=color, hovercolor=hovercolor)
    
def create_bins(n, bounds, log=False):
    if not log:
        return numpy.linspace(bounds[0], bounds[1], n)
    else:
        if bounds[0]<10**-10:
            bounds[0] = 10**-10
        return numpy.logspace(numpy.log(bounds[0]), numpy.log(bounds[1]), n, base=numpy.e)


# =======================================
# Main
def main():
    pass

if __name__ == '__main__':
    main()
    