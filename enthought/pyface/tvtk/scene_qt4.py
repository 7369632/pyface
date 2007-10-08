#------------------------------------------------------------------------------
# Copyright (c) 2005, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD
# license included in enthought/LICENSE.txt and may be redistributed only
# under the conditions described in the aforementioned license.  The license
# is also available online at http://www.enthought.com/licenses/BSD.txt
# Thanks for using Enthought open source!
#
# Author: Enthought, Inc.
# Description: <Enthought pyface package component>
#------------------------------------------------------------------------------

"""A VTK interactor scene widget for the PyFace PyQt backend.  See the class
docs for more details.
"""

# Author: Prabhu Ramachandran <prabhu_r@users.sf.net>
# Copyright (c) 2004-2007, Enthought, Inc.
# License: BSD Style.


import sys
import os
import tempfile

from PyQt4 import QtCore, QtGui

from enthought.tvtk.api import tvtk
from enthought.traits.api import Instance, Button, Any
from enthought.traits.ui.api import View, Group, Item, InstanceEditor

from enthought.pyface.api import Widget
from enthought.pyface.tvtk import picker
from enthought.pyface.tvtk import light_manager
from enthought.pyface.tvtk.tvtk_scene import TVTKScene

#from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from QVTKRenderWindowInteractor import QVTKRenderWindowInteractor


######################################################################
# `_VTKRenderWindowInteractor` class.
######################################################################
class _VTKRenderWindowInteractor(QVTKRenderWindowInteractor):
    """ This is a thin wrapper around the standard VTK PyQt interactor.
    """
    def __init__(self, scene, parent, **kwargs):
        QVTKRenderWindowInteractor.__init__(self, parent, **kwargs)

        self._scene = scene

    def resizeEvent(self, e):
        """ Reimplemented to refresh the traits of the render window.
        """
        QVTKRenderWindowInteractor.resizeEvent(self, e)

        self._scene._renwin.update_traits()

    def paintEvent(self, e):
        """ Reimplemented to create the light manager only when needed.  This
        is necessary because it makes sense to create the light manager only
        when the widget is realized.  Only when the widget is realized is the
        VTK render window created and only then are the default lights all
        setup correctly.
        """
        QVTKRenderWindowInteractor.paintEvent(self, e)

        scene = self._scene

        if scene.light_manager is None:
            scene.light_manager = light_manager.LightManager(scene)
            scene._renwin.update_traits()

    def keyPressEvent(self, e):
        """ This method is overridden to prevent the 's'/'w'/'e'/'q' keys from
        doing the default thing which is generally useless.  It also handles
        the 'p' and 'l' keys so the picker and light manager are called.
        """
        key = e.key()
        modifiers = e.modifiers()

        scene = self._scene
        camera = scene.camera

        if key in [QtCore.Qt.Key_S, QtCore.Qt.Key_W, QtCore.Qt.Key_E, QtCore.Qt.Key_Q]:
            return

        if key in [QtCore.Qt.Key_Minus]:
            camera.zoom(0.8)
            scene.render()
            return

        if key in [QtCore.Qt.Key_Equal, QtCore.Qt.Key_Plus]:
            camera.zoom(1.25)
            scene.render()
            return

        if key in [QtCore.Qt.Key_P] and modifiers == QtCore.Qt.NoModifier:
            pos = self.mapFromGlobal(QtGui.QCursor.pos())
            x = pos.x()
            y = self.height() - pos.y()
            scene.picker.pick(x, y)
            return

        if key in [QtCore.Qt.Key_L] and modifiers == QtCore.Qt.NoModifier:
            scene.light_manager.configure()
            return

        shift = ((modifiers & QtCore.Qt.ShiftModifier) == QtCore.Qt.ShiftModifier)

        if key == QtCore.Qt.Key_Left:
            if shift:
                camera.yaw(-5)
            else:
                camera.azimuth(5)

            scene.render()
            return

        if key == QtCore.Qt.Key_Right:
            if shift:
                camera.yaw(5)
            else:
                camera.azimuth(-5)

            scene.render()
            return

        if key == QtCore.Qt.Key_Up:
            if shift:
                camera.pitch(-5)
            else:
                camera.elevation(-5)

            camera.orthogonalize_view_up()
            scene.render()
            return

        if key == QtCore.Qt.Key_Down:
            if shift:
                camera.pitch(5)
            else:
                camera.elevation(5)

            camera.orthogonalize_view_up()
            scene.render()
            return

        QVTKRenderWindowInteractor.keyPressEvent(self, e)


######################################################################
# `FullScreen` class.
######################################################################
class FullScreen(object):
    """Creates a full screen interactor widget.  This will use VTK's
    event loop until the user presses 'q'/'e' on the full screen
    window.  This does not yet support interacting with any widgets on
    the renderered scene.

    This class is really meant to be used for VTK versions earlier
    than 5.1 where there was a bug with reparenting a window.

    """
    def __init__(self, scene):
        self.scene = scene
        self.old_rw = scene.render_window
        self.ren = scene.renderer

    def run(self):
        # Remove the renderer from the current render window.
        self.old_rw.remove_renderer(self.ren)

        # Creates renderwindow tha should be used ONLY for
        # visualization in full screen
        full_rw = tvtk.RenderWindow(stereo_capable_window=True,
                                    full_screen=True
                                    )
        # add the current visualization
        full_rw.add_renderer(self.ren)

        # Under OS X there is no support for creating a full screen
        # window so we set the size of the window here.
        # FIXME: Is this problem wx specific?
        if sys.platform  == 'darwin':
            full_rw.size = tuple(wx.GetDisplaySize())

        # provides a simple interactor
        style = tvtk.InteractorStyleTrackballCamera()
        self.iren = tvtk.RenderWindowInteractor(render_window=full_rw,
                                                interactor_style=style)

        # Gets parameters for stereo visualization
        if self.old_rw.stereo_render:
            full_rw.set(stereo_type=self.old_rw.stereo_type, stereo_render=True)

        # Starts the interactor
        self.iren.initialize()
        self.iren.render()
        self.iren.start()

        # Once the full screen window is quit this releases the
        # renderer before it is destroyed, and return it to the main
        # renderwindow.
        full_rw.remove_renderer(self.ren)
        self.old_rw.add_renderer(self.ren)
        self.old_rw.render()
        self.iren.disable()


######################################################################
# `Scene` class.
######################################################################
class Scene(TVTKScene, Widget):
    """A VTK interactor scene widget for pyface and PyQt.

    This widget uses a RenderWindowInteractor and therefore supports
    interaction with VTK widgets.  The widget uses TVTK.  In addition
    to the features that the base TVTKScene provides this widget
    supports:

    - saving the rendered scene to the clipboard.

    - picking data on screen.  Press 'p' or 'P' when the mouse is over
      a point that you need to pick.

    - The widget also uses a light manager to manage the lighting of
      the scene.  Press 'l' or 'L' to activate a GUI configuration
      dialog for the lights.

    - Pressing the left, right, up and down arrow let you rotate the
      camera in those directions.  When shift-arrow is pressed then
      the camera is panned.  Pressing the '+' (or '=')  and '-' keys
      let you zoom in and out.

    - full screen rendering via the full_screen button on the UI.

    """

    # The version of this class.  Used for persistence.
    __version__ = 0

    ###########################################################################
    # Traits.
    ###########################################################################

    # Turn on full-screen rendering.
    full_screen = Button('Full Screen')

    # The picker handles pick events.
    picker = Instance(picker.Picker)

    ########################################

    # Render_window's view.
    _stereo_view = Group(Item(name='stereo_render'),
                         Item(name='stereo_type'),
                         show_border=True,
                         label='Stereo rendering',
                         )

    # The default view of this object.
    default_view = View(Group(
                            Group(Item(name='background'),
                                  Item(name='foreground'),
                                  Item(name='parallel_projection'),
                                  Item(name='disable_render'),
                                  Item(name='off_screen_rendering'),
                                  Item(name='jpeg_quality'),
                                  Item(name='jpeg_progressive'),
                                  Item(name='magnification'),
                                  Item(name='anti_aliasing_frames'),
                                  Item(name='full_screen',
                                       show_label=False),
                                  ),
                            Group(Item(name='render_window',
                                       style='custom',
                                       visible_when='object.stereo',
                                       editor=InstanceEditor(view=View(_stereo_view)),
                                       show_label=False),
                                  ),
                            label='Scene'),
                        Group( Item(name='light_manager',
                                style='custom', show_label=False),
                                label='Lights')
                        )

    ########################################
    # Private traits.

    _vtk_control = Instance(_VTKRenderWindowInteractor)
    _fullscreen = Any

    ###########################################################################
    # 'object' interface.
    ###########################################################################
    def __init__(self, parent=None, **traits):
        """ Initializes the object. """

        # Base class constructor.
        super(Scene, self).__init__(parent, **traits)

        # Setup the default picker.
        self.picker = picker.Picker(self)

        # The light manager needs creating.
        self.light_manager = None

    def __get_pure_state__(self):
        """Allows us to pickle the scene."""
        # The control attribute is not picklable since it is a VTK
        # object so we remove it.
        d = super(Scene, self).__get_pure_state__()
        for x in ['_vtk_control', '_fullscreen']:
            d.pop(x, None)
        return d

    ###########################################################################
    # 'Scene' interface.
    ###########################################################################
    def render(self):
        """ Force the scene to be rendered. Nothing is done if the
        `disable_render` trait is set to True."""
        if not self.disable_render:
            self._vtk_control.Render()

    def get_size(self):
        """Return size of the render window."""
        sz = self._vtk_control.size()

        return (sz.width(), sz.height())

    def set_size(self, size):
        """Set the size of the window."""
        self._vtk_control.resize(*size)

    ###########################################################################
    # 'TVTKScene' interface.
    ###########################################################################
    def save_to_clipboard(self):
        """Saves a bitmap of the scene to the clipboard."""
        handler, name = tempfile.mkstemp()
        self.save_bmp(name)
        QtGui.QApplication.clipboard().setImage(QtGui.QImage(name))
        os.close(handler)
        os.unlink(name)

    ###########################################################################
    # Non-public interface.
    ###########################################################################
    def _create_control(self, parent):
        """ Create the toolkit-specific control that represents the widget. """

        # Create the VTK widget.
        self._vtk_control = window = _VTKRenderWindowInteractor(self, parent,
                                                                 stereo=self.stereo)

        # Switch the default interaction style to the trackball one.
        window.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

        # Grab the renderwindow.
        renwin = self._renwin = tvtk.to_tvtk(window.GetRenderWindow())
        renwin.set(point_smoothing=self.point_smoothing,
                   line_smoothing=self.line_smoothing,
                   polygon_smoothing=self.polygon_smoothing)
        # Create a renderer and add it to the renderwindow
        self._renderer = tvtk.Renderer()
        renwin.add_renderer(self._renderer)

        # Sync various traits.
        self.sync_trait('background', self._renderer)
        self.renderer.on_trait_change(self.render, 'background')
        self.sync_trait('parallel_projection', self.camera)
        self.sync_trait('off_screen_rendering', self._renwin)
        self.render_window.on_trait_change(self.render, 'off_screen_rendering')
        self.render_window.on_trait_change(self.render, 'stereo_render')
        self.render_window.on_trait_change(self.render, 'stereo_type')
        self.camera.on_trait_change(self.render, 'parallel_projection')

        self._interactor = tvtk.to_tvtk(window._Iren)

        return window

    def _lift(self):
        """Lift the window to the top. Useful when saving screen to an
        image."""
        if self.render_window.off_screen_rendering:
            # Do nothing if off screen rendering is being used.
            return

        self._vtk_control.window().raise_()
        QtCore.QCoreApplication.processEvents()

    def _full_screen_fired(self):
        fs = self._fullscreen
        if fs is None:
            f = FullScreen(self)
            f.run() # This will block.
            self._fullscreen = None
