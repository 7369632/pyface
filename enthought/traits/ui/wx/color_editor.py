#------------------------------------------------------------------------------
#
#  Copyright (c) 2005, Enthought, Inc.
#  All rights reserved.
#  
#  This software is provided without warranty under the terms of the BSD
#  license included in enthought/LICENSE.txt and may be redistributed only
#  under the conditions described in the aforementioned license.  The license
#  is also available online at http://www.enthought.com/licenses/BSD.txt
#
#  Thanks for using Enthought open source!
#------------------------------------------------------------------------------

""" Defines the various color editors for the Wx user interface toolkit.
"""

#-------------------------------------------------------------------------------
#  Imports:
#-------------------------------------------------------------------------------

import wx
import wx.combo

from enthought.traits.api import List, TraitError
from enthought.traits.ui.editors.color_editor \
    import ToolkitEditorFactory as BaseToolkitEditorFactory

from editor_factory import SimpleEditor as BaseSimpleEditor
from editor_factory import ReadonlyEditor as BaseReadonlyEditor
from editor_factory import TextEditor as BaseTextEditor

from color_trait import w3c_color_database
from helper import TraitsUIPanel

# Version dependent imports (ColourPtr not defined in wxPython 2.5):
try:
    ColorTypes = (wx.Colour, wx.ColourPtr)
except:
    ColorTypes = wx.Colour

#---------------------------------------------------------------------------
#  The Wx ToolkitEditorFactory class.
#---------------------------------------------------------------------------

class ToolkitEditorFactory(BaseToolkitEditorFactory):
    """ Wx editor factory for color editors.
    """
    
    def to_wx_color ( self, editor ):
        """ Gets the wxPython color equivalent of the object trait.
        """
        if self.mapped:
            attr = getattr( editor.object, editor.name + '_' )
        else:
            attr = getattr( editor.object, editor.name )
           
        if isinstance(attr, tuple):
            attr = wx.Colour( *[ int( round( c * 255.0 ) )
                             for c in attr ] )
        return attr
           
         
    #---------------------------------------------------------------------------
    #  Gets the application equivalent of a wxPython value:
    #---------------------------------------------------------------------------
        
    def from_wx_color ( self, color ):
        """ Gets the application equivalent of a wxPython value.
        """
        return color.Red(), color.Green(), color.Blue()
           
    #---------------------------------------------------------------------------
    #  Returns the text representation of a specified color value:
    #---------------------------------------------------------------------------
      
    def str_color ( self, color ):
        """ Returns the text representation of a specified color value.
        """
        if isinstance( color, ColorTypes ):
            alpha = color.Alpha()
            if alpha == 255:
                return "rgb(%d,%d,%d)" % (
                        color.Red(), color.Green(), color.Blue() )
   
            return "rgb(%d,%d,%d,%d)" % (
                    color.Red(), color.Green(), color.Blue(), alpha )
               
        return color


#-------------------------------------------------------------------------------
#  'ColorComboBox' class:
#-------------------------------------------------------------------------------

class ColorComboBox(wx.combo.OwnerDrawnComboBox):
    def OnDrawItem(self, dc, rect, item, flags):

        color_name = self.GetString(item)
        color = w3c_color_database.Find(color_name)
#        color = wx.Colour()
#        color.SetFromName(color_name)

        
        r = wx.Rect(rect.x, rect.y, rect.width, rect.height)
        r.Deflate(3, 0)
        
        dc.DrawText(color_name, r.x + 3, 
                    r.y + (r.height - dc.GetCharHeight())/2)
        
        swatch_size = r.height - 2
        
        brush = wx.Brush(color)
        dc.SetBrush(brush)
        dc.DrawRectangle(r.x + r.width - swatch_size, r.y+1,
                         swatch_size, swatch_size)
    
#-------------------------------------------------------------------------------
#  'SimpleColorEditor' class:
#-------------------------------------------------------------------------------

class SimpleColorEditor ( BaseSimpleEditor ):
    """ Simple style of color editor, which displays a text field whose 
    background color is the color value. Selecting the text field displays
    a dialog box for selecting a new color value.
    """
    
    #---------------------------------------------------------------------------
    #  Invokes the pop-up editor for an object trait:
    #---------------------------------------------------------------------------
    
    choices = List()
    
    def _choices_default(self):
        """ by default, uses the W3C 16 color names.
        """
        return ['aqua', 'black', 'blue', 'fuchsia', 'gray', 'green', 
                'lime', 'maroon', 'navy', 'olive', 'purple', 'red', 
                'silver', 'teal', 'white', 'yellow'] 
 
    def init ( self, parent ):
        """
        Finishes initializing the editor by creating the underlying widget.
        """
        
        current_color_name = self.value.GetAsString()
        if current_color_name not in self.choices:
            self.choices.insert(0, current_color_name)
        
        self.control = ColorComboBox(parent, -1, current_color_name,
                                wx.Point( 0, 0 ), wx.Size( -1, -1 ), self.choices,
                                style = wx.wx.CB_READONLY)
        
        self.control.Bind(wx.EVT_COMBOBOX, self.color_selected)                
        return

    #---------------------------------------------------------------------------
    #  Updates the editor when the object trait changes external to the editor:
    #---------------------------------------------------------------------------

    def update_editor ( self ):
        """ Updates the editor when the object trait changes externally to the 
            editor.
        """
        self.control.SetValue(self.value.GetAsString())


    def color_selected(self, event):
        """
        Event for when color is selected
        """
        
        color_name = self.choices[event.Selection]
        try:
            color = w3c_color_database.Find(color_name)
#            color = wx.Colour()
#            color.SetFromName(color_name)
            self.value = color
        except ValueError:
            pass
            
        return

#-------------------------------------------------------------------------------
#  'CustomColorEditor' class:
#-------------------------------------------------------------------------------

class CustomColorEditor ( BaseSimpleEditor ):
    """ Simple style of color editor, which displays a text field whose 
    background color is the color value. Selecting the text field displays
    a dialog box for selecting a new color value.
    """
    
    #---------------------------------------------------------------------------
    #  Invokes the pop-up editor for an object trait:
    #---------------------------------------------------------------------------
 
    def init ( self, parent ):
        """
        Finishes initializing the editor by creating the underlying widget.
        """
        self.control = self._panel = parent = TraitsUIPanel( parent, -1 )
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        text_control = wx.TextCtrl( parent, -1, self.str_value, 
                                    style = wx.TE_PROCESS_ENTER )
        wx.EVT_KILL_FOCUS( text_control, self.update_object )
        wx.EVT_TEXT_ENTER( parent, text_control.GetId(), self.update_object )
        
        button_control = wx.Button(parent, label='Edit', style=wx.BU_EXACTFIT)
        wx.EVT_BUTTON( button_control, button_control.GetId(), self.open_color_dialog )
        
        sizer.Add(text_control, wx.ALIGN_LEFT)
        sizer.AddSpacer(8)
        sizer.Add(button_control, wx.ALIGN_RIGHT)
        self.control.SetSizer(sizer)
        
        self._text_control = text_control
        self._button_control = button_control
        
        self.set_tooltip()
        
        return


    def update_object ( self, event ):
        """ Handles the user changing the contents of the edit control.
        """
        if not isinstance(event, wx._core.CommandEvent):
            return
        try:
            self.value = w3c_color_database.Find(self.control.GetValue())
            set_color( self )            
        except TraitError:
            pass
        
    def set_color(self, color):
        self._text_control.SetBackgroundColour(self.value)
        self._text_control.SetValue(self.string_value(self.value))

    #---------------------------------------------------------------------------
    #  Updates the editor when the object trait changes external to the editor:
    #---------------------------------------------------------------------------

    def update_editor ( self ):
        """ Updates the editor when the object trait changes externally to the 
            editor.
        """
        self.set_color(self.value)
        
    def open_color_dialog(self, event):
        """ Opens the color dialog and sets the value upon return
        """
        color_data = wx.ColourData()
        color_data.SetColour(self.value)
        
        color_dialog = wx.ColourDialog(self.control, color_data)
        color_dialog.ShowModal()
        
        color = color_dialog.GetColourData().GetColour()
        self.value = color
        self.set_color(self)
        

    def color_selected(self, event):
        """
        Event for when color is selected
        """
        color = event.GetColour()
        try:
            self.value = self.factory.from_wx_color(color)
        except ValueError:
            pass
            
        return
    
    def string_value ( self, color ):
        """ Returns the text representation of a specified color value.
        """
        color_name = w3c_color_database.FindName(color)
        if color_name != '':
            return color_name

        return self.factory.str_color( color ) 
    

#-------------------------------------------------------------------------------
#  'ReadonlyColorEditor' class:
#-------------------------------------------------------------------------------

class ReadonlyColorEditor ( BaseReadonlyEditor ):
    """ Read-only style of color editor, which displays a read-only text field
    whose background color is the color value.
    """
    
    #---------------------------------------------------------------------------
    #  Finishes initializing the editor by creating the underlying toolkit
    #  widget:
    #---------------------------------------------------------------------------

    def init ( self, parent ):
        """ Finishes initializing the editor by creating the underlying toolkit
            widget.
        """
        self.control = wx.TextCtrl(parent, style=wx.TE_READONLY)

    #---------------------------------------------------------------------------
    #  Updates the editor when the object trait changes external to the editor:
    #---------------------------------------------------------------------------

    def update_editor ( self ):
        """ Updates the editor when the object trait changes externally to the 
            editor.
        """
        #super( ReadonlyColorEditor, self ).update_editor()
        self.control.SetValue(self.string_value(self.value))
        set_color( self )

    #---------------------------------------------------------------------------
    #  Returns the text representation of a specified color value:
    #---------------------------------------------------------------------------

    def string_value ( self, color ):
        """ Returns the text representation of a specified color value.
        """
        color_name = w3c_color_database.FindName(color)
        if color_name != '':
            return color_name

        return self.factory.str_color( color ) 

#-------------------------------------------------------------------------------
#  'ReadonlyColorEditor' class:
#-------------------------------------------------------------------------------

class TextColorEditor ( BaseTextEditor ):
    """ Text style of color editor, which displays a text field
    whose background color is the color value.
    """
    
    #---------------------------------------------------------------------------
    #  Updates the editor when the object trait changes external to the editor:
    #---------------------------------------------------------------------------

    def update_editor ( self ):
        """ Updates the editor when the object trait changes externally to the 
            editor.
        """
        self.control.SetValue(self.string_value(self.value))
        set_color( self )

    def update_object ( self, event ):
        """ Handles the user changing the contents of the edit control.
        """
        if not isinstance(event, wx._core.CommandEvent):
            return
        try:
            self.value = w3c_color_database.Find(self.control.GetValue())
            set_color( self )            
        except TraitError:
            pass

    #---------------------------------------------------------------------------
    #  Returns the text representation of a specified color value:
    #---------------------------------------------------------------------------

    def string_value ( self, color ):
        """ Returns the text representation of a specified color value.
        """
        color_name = w3c_color_database.FindName(color)
        if color_name != '':
            return color_name

        return self.factory.str_color( color ) 

#-------------------------------------------------------------------------------
#   Sets the color of the specified editor's color control: 
#-------------------------------------------------------------------------------

def set_color ( editor ):
    """  Sets the color of the specified color control.
    """
    color = editor.factory.to_wx_color(editor)
    editor.control.SetBackgroundColour(color)


# Define the SimpleEditor, CustomEditor, etc. classes which are used by the
# editor factory for the color editor.
SimpleEditor = SimpleColorEditor
CustomEditor = CustomColorEditor
TextEditor = TextColorEditor
ReadonlyEditor = ReadonlyColorEditor
