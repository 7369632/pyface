# Standard library imports
from contextlib import contextmanager

# Enthought library imports.
from enthought.pyface.tasks.i_dock_pane import IDockPane, MDockPane
from enthought.traits.api import Bool, Property, Tuple, implements, \
    on_trait_change

# System library imports.
from enthought.qt import QtCore, QtGui

# Local imports.
from task_pane import TaskPane

# Constants.
area_map = { 'left'   : QtCore.Qt.LeftDockWidgetArea,
             'right'  : QtCore.Qt.RightDockWidgetArea,
             'top'    : QtCore.Qt.TopDockWidgetArea,
             'bottom' : QtCore.Qt.BottomDockWidgetArea }
reverse_area_map = dict((v, k) for k, v in area_map.iteritems())


class DockPane(TaskPane, MDockPane):
    """ The toolkit-specific implementation of a DockPane.

    See the IDockPane interface for API documentation.
    """

    implements(IDockPane)

    #### 'IDockPane' interface ################################################

    size = Property(Tuple)

    #### Protected traits #####################################################

    _receiving = Bool(False)

    ###########################################################################
    # 'ITaskPane' interface.
    ###########################################################################

    def create(self, parent):
        """ Create and set the dock widget that contains the pane contents.
        """
        self.control = control = QtGui.QDockWidget(parent)

        # Set the widget's object name. This important for QMainWindow state
        # saving. Use the task ID and the pane ID to avoid collisions when a
        # pane is present in multiple tasks attached to the same window.
        control.setObjectName(self.task.id + ':' + self.id)

        # Configure the dock widget according to the DockPane settings.
        self._set_dock_features()
        self._set_dock_title()
        self._set_floating()
        self._set_visible()

        # Connect signal handlers for updating DockPane traits.
        control.dockLocationChanged.connect(self._receive_dock_area)
        control.topLevelChanged.connect(self._receive_floating)
        control.visibilityChanged.connect(self._receive_visible)

        # Add the pane contents to the dock widget.
        contents = self.create_contents(control)
        control.setWidget(contents)

        # Hide the control by default. Otherwise, the widget will visible in its
        # parent immediately!
        control.hide()

    ###########################################################################
    # 'IDockPane' interface.
    ###########################################################################

    def create_contents(self, parent):
        """ Create and return the toolkit-specific contents of the dock pane.
        """
        return QtGui.QWidget(parent)

    ###########################################################################
    # Protected interface.
    ###########################################################################

    @contextmanager
    def _signal_context(self):
        """ Defines a context appropriate for Qt signal callbacks. Necessary to
            prevent feedback between Traits and Qt event handlers.
        """
        original = self._receiving
        self._receiving = True
        yield
        self._receiving = original

    #### Trait property getters/setters #######################################

    def _get_size(self):
        if self.control is not None:
            return (self.control.width(), self.control.height())
        return (-1, -1)

    #### Trait change handlers ################################################

    @on_trait_change('dock_area')
    def _set_dock_area(self):
        if self.control is not None and not self._receiving:
            # Only attempt to adjust the area if the task is active.
            main_window = self.task.window.control
            if main_window and self.task == self.task.window.active_task:
                # Qt will automatically remove the dock widget from its previous
                # area, if it had one.
                main_window.addDockWidget(area_map[self.dock_area], 
                                          self.control)

    @on_trait_change('closable', 'floatable', 'movable')
    def _set_dock_features(self):
        if self.control is not None:
            features = QtGui.QDockWidget.NoDockWidgetFeatures
            if self.closable:
                features |= QtGui.QDockWidget.DockWidgetClosable
            if self.floatable:
                features |= QtGui.QDockWidget.DockWidgetFloatable
            if self.movable:
                features |= QtGui.QDockWidget.DockWidgetMovable
            self.control.setFeatures(features)

    @on_trait_change('name')
    def _set_dock_title(self):
        if self.control is not None:
            self.control.setWindowTitle(self.name)

    @on_trait_change('floating')
    def _set_floating(self):
        if self.control is not None and not self._receiving:
            self.control.setFloating(self.floating)

    @on_trait_change('visible')
    def _set_visible(self):
        if self.control is not None and not self._receiving:
            self.control.setVisible(self.visible)

    #### Signal handlers ######################################################

    def _receive_dock_area(self, area):
        with self._signal_context():
            self.dock_area = reverse_area_map[area]

    def _receive_floating(self, floating):
        with self._signal_context():
            self.floating = floating

    def _receive_visible(self):
        with self._signal_context():
            if self.control is not None:
                self.visible = self.control.isVisible()
