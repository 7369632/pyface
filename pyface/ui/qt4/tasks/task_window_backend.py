# Standard library imports.
import logging

# System library imports.
from enthought.qt import QtCore, QtGui

# Local imports.
from dock_pane import area_map
from enthought.pyface.tasks.i_task_window_backend import MTaskWindowBackend
from enthought.pyface.tasks.task import TaskLayout

# Logging.
logger = logging.getLogger(__name__)


class TaskWindowBackend(MTaskWindowBackend):
    """ The toolkit-specific implementation of a TaskWindowBackend.

    See the ITaskWindowBackend interface for API documentation.
    """

    ###########################################################################
    # 'ITaskWindowBackend' interface.
    ###########################################################################

    def create_contents(self, parent):
        """ Create and return the TaskWindow's contents.
        """
        return QtGui.QStackedWidget(parent)

    def hide_task(self, state):
        """ Assuming the specified TaskState is active, hide its controls.
        """
        # Save the task's layout in case it is shown later.
        layout = self.window._active_state.layout
        layout.toolkit_state = self.control.saveState()

        # Now hide its controls.
        self.control.centralWidget().removeWidget(state.central_pane.control)
        for dock_pane in state.dock_panes:
            # Warning: The layout behavior is subtly different (and wrong!) if
            # the order of these two statement is switched.
            dock_pane.control.hide()
            self.control.removeDockWidget(dock_pane.control)

    def show_task(self, state):
        """ Assumming no task is currently active, show the controls of the
            specified TaskState.
        """
        # Show the central pane.
        self.control.centralWidget().addWidget(state.central_pane.control)

        # Show the dock panes.
        self._layout_state(state)

        # OSX-specific: if there is only a single tool bar, it doesn't matter if
        # the user can drag it around or not. Therefore, we can combine it with
        # the title bar, which is idiomatic on the Mac.
        self.control.setUnifiedTitleAndToolBarOnMac(
            len(state.tool_bar_managers) <= 1)

    #### Methods for saving and restoring the layout ##########################

    def get_layout(self):
        """ Returns a TaskLayout for the current state of the window.
        """
        layout = self.window._active_state.layout.clone_traits()
        layout.toolkit_state = self.control.saveState()
        return layout

    def set_layout(self, layout):
        """ Applies a TaskLayout (which should be suitable for the active task)
            to the window.
        """
        self.window._active_state.layout = layout.clone_traits()
        self._layout_state(self.window._active_state)

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _add_dock_pane(self, dock_pane, area=None):
        """ Adds a DockPane's QDockWidget to the main window.
        """
        if area is None:
            area = dock_pane.dock_area
        self.control.addDockWidget(area_map[area], dock_pane.control)

    def _layout_area(self, area, state):
        """ Layout the dock panes in the specified area of the given TaskState.
            Returns the list of dock panes processed for the area.
        """
        panes = []
        pane_ids = getattr(state.layout, area + '_panes')
        for group_ids in pane_ids:
            # Transform the degenerate case into the general case.
            if isinstance(group_ids, basestring):
                group_ids = [ group_ids ]

            # Add the first dock pane in the group normally and tabify the
            # others.
            first_pane = None
            for pane_id in group_ids:
                dock_pane = state.get_dock_pane(pane_id)
                if dock_pane:
                    self._add_dock_pane(dock_pane, area)
                    if first_pane:
                        self.control.tabifyDockWidget(first_pane.control,
                                                      dock_pane.control)
                    else:
                        first_pane = dock_pane
                    dock_pane.control.show()
                    panes.append(dock_pane)
                else:
                    logger.warn("Pane layout: task %r does not contain pane "
                                "with id %r." % (state.task, pane_id))
                    
            # Activate the first (left-most) pane in the tab group by default.
            if first_pane:
                first_pane.control.raise_()

        return panes

    def _layout_state(self, state):
        """ Layout the dock panes in the specified TaskState using its
            TaskLayout.
        """
        # If a Qt-specific state string is attached to the layout, prefer it.
        # If at any point the state restore fails, fall back to the
        # toolkit-independent layout.
        layout = state.layout
        restored = False
        if layout.toolkit_state is not None:
            restored = self.control.restoreState(layout.toolkit_state)

        # Layout the panes according to toolkit-indepedent TaskLayout API.
        if not restored:
            processed_panes = []
            for area in ('left', 'right', 'top', 'bottom'):
                processed_panes.extend(self._layout_area(area, state))

            # Add all panes not assigned an area by the TaskLayout.
            for dock_pane in state.dock_panes:
                if dock_pane not in processed_panes:
                    self._add_dock_pane(dock_pane)
