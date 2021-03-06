from copy import deepcopy
import tkinter


"""
Utility functions and data structures.
"""

__all__ = ["ObservableSet", "AttrDict", "CanvasToolTip"]


class ObservableSet(set):
    """
    An observable set is a set that notifies all its registered observers
    each time the set of modified.
    """

    def __init__(self, *args, **kwargs):
        super(ObservableSet, self).__init__(*args, **kwargs)
        self._observers = []

    def register(self, observer):
        """
        Register the observer of this set. The observer will be notified
        through its "update" method every time the set is modified.

        :param observer: the observer; supports the "update(set)" method.
        """
        self._observers.append(observer)

    def unregister(self, observer):
        """
        Unregister the given observer. It will not be notified any more.

        :param observer: the observer to remove.
        """
        try:
            self._observers.remove(observer)
        except ValueError:
            pass

    def notify(self):
        """
        Force this set to notify all its observers.
        """
        for observer in self._observers:
            observer.update(self)

    @classmethod
    def _wrap_methods(cls, names):
        def wrap_method_closure(name):
            def inner(self, *args):
                old = ObservableSet(self)
                result = getattr(super(cls, self), name)(*args)
                if isinstance(result, set):
                    result = cls(result)
                if old != self:
                    self.notify()
                return result

            inner.fn_name = name
            setattr(cls, name, inner)

        for name in names:
            wrap_method_closure(name)


ObservableSet._wrap_methods(['__ror__', 'difference_update', '__isub__',
                             'symmetric_difference', '__rsub__', '__and__',
                             '__rand__', 'intersection',
                             'difference', '__iand__', 'union', '__ixor__',
                             'symmetric_difference_update', '__or__', 'copy',
                             '__rxor__',
                             'intersection_update', '__xor__', '__ior__',
                             '__sub__', 'add', 'remove',
                             'clear', 'discard', 'update'
                             ])


class AttrDict(dict):
    """
    A dictionary where keys can be accessed as attributes.
    """

    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    def __deepcopy__(self, memo):
        return AttrDict(deepcopy(dict(self), memo=memo))


class CanvasToolTip:
    """
    Modified from http://tkinter.unpythonic.net/wiki/ToolTip

    Michael Lange <klappnase (at) freakmail (dot) de>

    The ToolTip class provides a flexible tooltip widget for tkinter; it is
    based on IDLE's ToolTip module which unfortunately seems to be broken (at
    least the version I saw).

    INITIALIZATION OPTIONS:

    anchor
        where the text should be positioned inside the widget, must be on of
        "n", "s", "e", "w", "nw" and so on;
        default is "center"
    bd
        borderwidth of the widget; default is 1
        (NOTE: don't use "borderwidth" here)
    bg
        background color to use for the widget;
        default is "lightyellow"
        (NOTE: don't use "background")
    delay
        time in ms that it takes for the widget to appear on the screen when
        the mouse pointer has entered the parent widget;
        default is 1500
    fg
        foreground (i.e. text) color to use;
        default is "black"
        (NOTE: don't use "foreground")
    follow_mouse
        if set to 1 the tooltip will follow the mouse pointer instead of being
        displayed outside of the parent widget; this may be useful if you want
        to use tooltips for large widgets like listboxes or canvases;
        default is 0
    font
        font to use for the widget; default is system specific
    justify
        how multiple lines of text will be aligned, must be "left", "right" or
        "center";
        default is "left"
    padx
        extra space added to the left and right within the widget;
        default is 4
    pady
        extra space above and below the text;
        default is 2
    relief
        one of "flat", "ridge", "groove", "raised", "sunken" or "solid";
        default is "solid"
    state
        must be "normal" or "disabled"; if set to "disabled" the tooltip will
        not appear;
        default is "normal"
    text
        the text that is displayed inside the widget
    textvariable
        if set to an instance of tkinter.StringVar() the variable's value will
        be used as text for the widget
    width
        width of the widget; the default is 0, which means that "wraplength"
        will be used to limit the widgets width
    wraplength
        limits the number of characters in each line;
        default is 150

    WIDGET METHODS:

    configure(**opts)
        change one or more of the widget's options as described above;
        the changes will take effect the next time the tooltip shows up;
        NOTE: follow_mouse cannot be changed after widget initialization

    Other widget methods that might be useful if you want to subclass ToolTip:

    enter()
        callback when the mouse pointer enters the parent widget
    leave()
        called when the mouse pointer leaves the parent widget
    motion()
        is called when the mouse pointer moves inside the parent widget if
        follow_mouse is set to 1 and the tooltip has shown up to continually
        update the coordinates of the tooltip window
    coords()
        calculates the screen coordinates of the tooltip window
    create_contents()
        creates the contents of the tooltip window (by default a tkinter.Label)

    """

    def __init__(self, canvas, handle, text='Your text here', delay=500,
                 **opts):
        self.canvas = canvas
        self._opts = {'anchor': 'center', 'bd': 1, 'bg': 'lightyellow',
                      'delay': delay, 'fg': 'black', 'follow_mouse': 0,
                      'font': None, 'justify': 'left', 'padx': 4, 'pady': 2,
                      'relief': 'solid', 'state': 'normal', 'text': text,
                      'textvariable': None, 'width': 0, 'wraplength': 150}
        self.configure(**opts)
        self._tipwindow = None
        self._id = None
        self._id1 = self.canvas.tag_bind(handle, "<Enter>", self.enter, '+')
        self._id2 = self.canvas.tag_bind(handle, "<Leave>", self.leave, '+')
        self._id3 = self.canvas.tag_bind(handle, "<ButtonPress>", self.leave,
                                         '+')
        self._follow_mouse = 0
        if self._opts['follow_mouse']:
            self._id4 = self.canvas.tag_bind(handle, "<Motion>", self.motion,
                                             '+')
            self._follow_mouse = 1

    def configure(self, **opts):
        for key in opts:
            if key in self._opts:
                self._opts[key] = opts[key]
            else:
                msg = 'KeyError: Unknown option: "{}"'.format(key)
                raise KeyError(msg)

    # these methods handle the callbacks on "<Enter>", "<Leave>" and <Motion>"
    # events on the parent widget;
    # override them if you want to change the widget's behavior

    def enter(self, event=None):
        self._schedule()

    def leave(self, event=None):
        self._unschedule()
        self._hide()

    def motion(self, event=None):
        if self._tipwindow and self._follow_mouse:
            x, y = self.coords()
            self._tipwindow.wm_geometry("+{:d}+{:d}".format(int(x), int(y)))

    # the methods that do the work:

    def _schedule(self):
        self._unschedule()
        if self._opts['state'] == 'disabled':
            return
        self._id = self.canvas.after(self._opts['delay'], self._show)

    def _unschedule(self):
        id_ = self._id
        self._id = None
        if id_:
            self.canvas.after_cancel(id_)

    def _show(self):
        if self._opts['state'] == 'disabled':
            self._unschedule()
            return
        if not self._tipwindow:
            self._tipwindow = tw = tkinter.Toplevel(self.canvas)
            # hide the window until we know the geometry
            tw.withdraw()
            tw.wm_overrideredirect(1)

            if tw.tk.call("tk", "windowingsystem") == 'aqua':
                tw.tk.call("::tk::unsupported::MacWindowStyle", "style", tw._w,
                           "help", "none")

            self.create_contents()
            tw.update_idletasks()
            x, y = self.coords()
            tw.wm_geometry("+{:d}+{:d}".format(int(x), int(y)))
            tw.deiconify()

    def _hide(self):
        tw = self._tipwindow
        self._tipwindow = None
        if tw:
            tw.destroy()

    # these methods might be overridden in derived classes:

    def coords(self):
        # The tip window must be completely outside the master widget;
        # otherwise when the mouse enters the tip window we get
        # a leave event and it disappears, and then we get an enter
        # event and it reappears, and so on forever :-(
        # or we take care that the mouse pointer is always outside the
        # tipwindow :-)
        tw = self._tipwindow
        twx, twy = tw.winfo_reqwidth(), tw.winfo_reqheight()
        w, h = tw.winfo_screenwidth(), tw.winfo_screenheight()
        # calculate the y coordinate:
        if self._follow_mouse:
            y = tw.winfo_pointery() + 20
            # make sure the tipwindow is never outside the screen:
            if y + twy > h:
                y = y - twy - 30
        else:
            y = self.canvas.winfo_rooty() + self.canvas.winfo_height() + 3
            if y + twy > h:
                y = self.canvas.winfo_rooty() - twy - 3
        # we can use the same x coord in both cases:
        x = tw.winfo_pointerx() - twx / 2
        if x < 0:
            x = 0
        elif x + twx > w:
            x = w - twx
        return x, y

    def create_contents(self):
        opts = self._opts.copy()
        for opt in ('delay', 'follow_mouse', 'state'):
            del opts[opt]
        label = tkinter.Label(self._tipwindow, **opts)
        label.pack()
