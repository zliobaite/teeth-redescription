import numpy as np

import pdb

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.mlab import dist_point_to_segment

class ResizeableRectangle(object):
    # draggable rectangle with the animation blit techniques; see
    # http://www.scipy.org/Cookbook/Matplotlib/Animations

    """
    Resizeable rectangle with the animation blit techniques.
    Based on example code at
http://matplotlib.sourceforge.net/users/event_handling.html
    If *allow_resize* is *True* the recatngle can be resized by dragging its
    lines. *border_tol* specifies how close the pointer has to be to a line for
    the drag to be considered a resize operation. Dragging is still possible by
    clicking the interior of the rectangle. *fixed_aspect_ratio* determines if
    the recatngle keeps its aspect ratio during resize operations.
    """
    lock = None  # only one can be animated at a time
    def __init__(self, rect, border_tol=.15, rid=None, callback=None, pinf=None, annotation=None, buttons_t=[3]):
        self.buttons_t = buttons_t
        self.callback = callback
        self.pinf = pinf
        self.annotation = annotation
        self.rid = rid
        self.rect = rect
        self.border_tol = border_tol
        self.press = None
        self.background = None

    def do_press(self, event):
        """on button press we will see if the mouse is over us and store some 
data"""
        if event.button not in self.buttons_t:
            return
        #print 'event contains', self.rect.xy
        x0, y0 = self.rect.xy
        w0, h0 = self.rect.get_width(), self.rect.get_height()
        aspect_ratio = np.true_divide(w0, h0)
        self.press = x0, y0, w0, h0, aspect_ratio, event.xdata, event.ydata

        # draw everything but the selected rectangle and store the pixel buffer
        canvas = self.rect.figure.canvas
        axes = self.rect.axes
        self.rect.set_animated(True)
        canvas.draw()
        self.background = canvas.copy_from_bbox(self.rect.axes.bbox)

        # now redraw just the rectangle
        axes.draw_artist(self.rect)

        # and blit just the redrawn area
        canvas.blit(axes.bbox)

    def do_motion(self, event):
        """on motion we will move the rect if the mouse is over us"""
        if event.button not in self.buttons_t:
            return
        x0, y0, w0, h0, aspect_ratio, xpress, ypress = self.press
        self.dx = event.xdata - xpress
        self.dy = event.ydata - ypress
        #self.rect.set_x(x0+dx)
        #self.rect.set_y(y0+dy)
        self.update_rect()

        canvas = self.rect.figure.canvas
        axes = self.rect.axes
        # restore the background region
        canvas.restore_region(self.background)

        # redraw just the current rectangle
        axes.draw_artist(self.rect)
        if self.annotation is not None:
            axes.draw_artist(self.annotation)

        # blit just the redrawn area
        canvas.blit(axes.bbox)
        # if self.annotation is not None:
        #     try:
        #         canvas.blit(self.annotation.get_bbox_patch())
        #     except AttributeError:
        #         print "Failed blit"

    def contains(self, event):
        if event.button in self.buttons_t:
            return self.rect.contains(event)
        else:
            return False, None
    
    def do_release(self, event):
        """on release we reset the press data"""
        if event.button not in self.buttons_t:
            return
        self.press = None
        if self.callback is not None:
            self.callback(self.rid, self.rect)

        # turn off the rect animation property and reset the background
        self.rect.set_animated(False)
        self.background = None

        # redraw the full figure
        self.rect.figure.canvas.draw()

    def update_rect(self):
        if self.press is None:
            return
        #### to force redraw of annotation, somehow blit ceased to function
        self.annotation = None
        
        x0, y0, w0, h0, aspect_ratio, xpress, ypress = self.press
        dy = self.dy
        bt = self.border_tol
        if abs(y0-ypress)<bt*h0:
            if h0-dy > 0:
                self.rect.set_y(y0+dy)
                self.rect.set_height(h0-dy)

                if self.annotation is not None:
                    b = y0+dy
                    if self.pinf is not None:
                        self.annotation.set_text("%s" % self.pinf(self.rid, b, -1))
                    else:
                        self.annotation.set_text("%s" % b)
                    self.annotation.xytext = (x0+0.25, b)
                    self.annotation.xy = (x0+0.25, b)

                else:
                    b = y0+dy
                    if self.pinf is not None:
                        self.annotation = self.rect.axes.annotate("%s" % self.pinf(self.rid, b, -1),
                                                            xy=(x0+0.25, b), xytext=(x0+0.25, b), backgroundcolor="w")
                    else:
                        self.annotation = self.rect.axes.annotate("%s" % b,
                                                            xy=(x0+0.25, b), xytext=(x0+0.25, b), backgroundcolor="w")

        elif abs(y0+h0-ypress)<bt*h0:
            if h0+dy > 0:
                self.rect.set_height(h0+dy)

                if self.annotation is not None:
                    b = y0+h0+dy
                    if self.pinf is not None:
                        self.annotation.set_text("%s" % self.pinf(self.rid, b, 1))
                    else:
                        self.annotation.set_text("%s" % b)
                    self.annotation.xytext = (x0+0.25, b)
                    self.annotation.xy = (x0+0.25, b)

                else:
                    b = y0+h0+dy
                    if self.pinf is not None:
                        self.annotation = self.rect.axes.annotate("%s" % self.pinf(self.rid, b, -1),
                                                            xy=(x0+0.25, b), xytext=(x0+0.25, b), backgroundcolor="w")
                    else:
                        self.annotation = self.rect.axes.annotate("%s" % b,
                                                            xy=(x0+0.25, b), xytext=(x0+0.25, b), backgroundcolor="w")


class DraggableRectangle(ResizeableRectangle):

    def update_rect(self):
        if self.press is None:
            return
        self.annotation = None

        x0, y0, w0, h0, aspect_ratio, xpress, ypress = self.press
        dy = self.dy
        bt = 1
        if abs(y0-ypress)<bt*h0:
            self.rect.set_y(y0+dy)

            if self.annotation is not None:
                b = y0+dy+h0/2.0
                if self.pinf is not None:
                    self.annotation.set_text("%s" % self.pinf(self.rid, b, -1))
                else:
                    self.annotation.set_text("%s" % b)
                self.annotation.xytext = (x0+0.25, b)
            else:
                b = y0+dy+h0/2.0
                if self.pinf is not None:
                    self.annotation = self.rect.axes.annotate("%s" % self.pinf(self.rid, b, -1),
                                                            xy=(x0+0.25, b), xytext=(x0+0.25, b), backgroundcolor="w")
                else:
                    self.annotation = self.rect.axes.annotate("%s" % b,
                                                            xy=(x0+0.25, b), xytext=(x0+0.25, b), backgroundcolor="w")

        elif abs(y0+h0-ypress)<bt*h0:
            self.rect.set_y(y0+dy)
            
            if self.annotation is not None:
                b = y0+dy+h0/2.0
                if self.pinf is not None:
                    self.annotation.set_text("%s" % self.pinf(self.rid, b, 1))
                else:
                    self.annotation.set_text("%s" % b)
                self.annotation.xytext = (x0+0.25, b)
            else:
                b = y0+dy+h0/2.0
                if self.pinf is not None:
                    self.annotation = self.rect.axes.annotate("%s" % self.pinf(self.rid, b, 1),
                                                            xy=(x0+0.25, b), xytext=(x0+0.25, b), backgroundcolor="w")
                else:
                    self.annotation = self.rect.axes.annotate("%s" % b,
                                                            xy=(x0+0.25, b), xytext=(x0+0.25, b), backgroundcolor="w")


class MaskCreator(object):
    """Interactive tool to draw mask on an image or image-like array.
    Adapted from matplotlib/examples/event_handling/poly_editor.py

    An interactive polygon editor.

    Parameters
    ----------
    poly_xy : list of (float, float)
        List of (x, y) coordinates used as vertices of the polygon.
    max_ds : float
        Max pixel distance to count as a vertex hit.

    Key-bindings
    ------------
    'd' : delete the vertex under point
    'i' : insert a vertex at point.  You must be within max_ds of the
          line connecting two existing vertices
    """
    pcolor = "#FFD700"
    
    def __init__(self, ax, poly_xy=None, max_ds=10, buttons_t=[1], callback_change=None):
        self.callback_change = callback_change
        self.last_pos = None
        self.buttons_t = buttons_t
        self.max_ds = max_ds
        ax.set_clip_on(False)
        self.ax = ax
        self.verts  = None
        if poly_xy is None:
            self.poly = None
        else:
            self.createPoly(poly_xy)

        self._ind = None # the active vert

        self.actions_map = {"kill": {"method": self.do_kill, "label": "Kill polygon vertex",
                                       "legend": "Delete the polygon vertex under pointer",
                                       "order":2, "active_q": self.q_false},
                            "add": {"method": self.do_add, "label": "Add polygon vertex",
                                       "legend": "Insert a polygon vertex at pointer", "order":1, "active_q": self.q_false},
                            "erase": {"method": self.do_erase, "label": "Erase polygon",
                                      "legend": "Erase the polygon", "order":3, "active_q": self.q_has_poly}
                            }
        self.setKeys()
        canvas = self.ax.figure.canvas
        canvas.mpl_connect('draw_event', self.draw_callback)
        canvas.mpl_connect('button_press_event', self.button_press_callback)
        canvas.mpl_connect('button_release_event', self.button_release_callback)
        canvas.mpl_connect('key_press_event', self.key_press_callback)
        canvas.mpl_connect('motion_notify_event', self.motion_notify_callback)
        self.canvas = canvas

    def q_false(self):
        return False

    def q_has_poly(self):
        return self.poly is not None

    def setButtons(self, buttons):
        self.buttons_t = buttons

    def getActionsDetails(self, off=0):
        details = []
        for action, dtl in self.actions_map.items():
            details.append({"label": "%s[%s]" % (dtl["label"].ljust(30), dtl["key"]),
                            "legend": dtl["legend"], "active": dtl["active_q"](),
                            "key": dtl["key"], "order": dtl["order"]+off, "type": "mc"})
        return details
    
    def setKeys(self, keys=None):
        self.keys_map = {}

        if keys is None:
            for action, details in self.actions_map.items():
                details["key"] = action[0]
                self.keys_map[details["key"]] = action
        else:
            for action, details in self.actions_map.items():
                details["key"] = None
            for key, action in keys.items():
                if action in self.actions_map:
                    self.actions_map[action]["key"] = key
                    self.keys_map[key] = action

    def isActive(self):
        return len(self.buttons_t) > 0

    def doActionForKeyEvent(self, event):
        return self.doActionForKey(event.key, event)

    def doActionForKey(self, key, event=None):
        if self.keys_map.get(key, None) in self.actions_map:
            self.actions_map[self.keys_map[key]]["method"](event)
            self.draw_callback(event)                
            if self.callback_change is not None:
                self.callback_change()
            return True
        return False
            
    def clear(self, review=True):
        self.verts  = None
        self.poly = None
        self._ind = None
        self.canvas.draw()

    def createPoly(self, poly_xy=None):
        self.poly = Polygon(poly_xy, animated=True,
                            fc=self.pcolor, ec=self.pcolor, alpha=0.3)
        self.ax.add_patch(self.poly)
        x, y = zip(*self.poly.xy)
        self.line = plt.Line2D(x, y, color=self.pcolor, lw=1, marker='o', mec=self.pcolor, ms=3, mew=2, mfc='k',
                               alpha=0.7, animated=True)
        self._update_line()
        self.ax.add_line(self.line)

        self.poly.add_callback(self.poly_changed)

    def get_path(self):
        if self.poly is not None:
            return self.poly.get_path()

    def poly_changed(self, poly):
        'this method is called whenever the polygon object is called'
        # only copy the artist props to the line (except visibility)
        vis = self.line.get_visible()
        #Artist.update_from(self.line, poly)
        self.line.set_visible(vis)  # don't use the poly visibility state

    def draw_callback(self, event):
        if self.poly is None:
            return
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        self.ax.draw_artist(self.poly)
        self.ax.draw_artist(self.line)
        self.canvas.blit(self.ax.bbox)

    def button_press_callback(self, event):
        'whenever a mouse button is pressed'
        ignore = event.inaxes is None or (event.button not in self.buttons_t)
        if ignore:
            return
        self._ind = self.get_ind_under_cursor(event)

    def button_release_callback(self, event):
        'whenever a mouse button is released'
        ignore = event.button not in self.buttons_t
        if ignore:
            return
        self._ind = None
        if self.callback_change is not None:
            self.callback_change()

    def do_kill(self, event=None):
        ind = self.get_ind_under_cursor(event)
        if ind is None:
            return
        if ind == 0 or ind == self.last_vert_ind:
            inds = [0, self.last_vert_ind]
        else:
            inds = [ind]
        if len(self.poly.xy) - len(inds) < 1: #
            self.poly = None
            return
        self.poly.xy = [tup for i,tup in enumerate(self.poly.xy)
                        if i not in inds]
        self._update_line()

    def do_erase(self, event=None):
        self.clear()

    def do_add(self,event=None):
        if event is None:
            if self.last_pos is None:
                return
            else:
                xpos, ypos, xdpos, ydpos = self.last_pos
        else:
            xdpos, ydpos = (event.xdata, event.ydata)
            xpos, ypos = (event.x, event.y)
        if self.poly is None:
            self.createPoly(np.array([(xdpos, ydpos)]))
            return 0
            
        if self.poly.xy.shape[0] < 4:
            i = 0
            self.poly.xy = np.array(
                    list(self.poly.xy[:i+1]) +
                    [(xdpos, ydpos)] +
                    list(self.poly.xy[i+1:]))
            self._update_line()
            return i+1
            
        xys = self.poly.get_transform().transform(self.poly.xy)
        for i in range(len(xys)-1):
            s0 = xys[i]
            s1 = xys[i+1]
            d = dist_point_to_segment((xpos, ypos), s0, s1)
            if d <= self.max_ds:
                self.poly.xy = np.array(
                    list(self.poly.xy[:i+1]) +
                    [(xdpos, ydpos)] +
                    list(self.poly.xy[i+1:]))
                self._update_line()
                return i+1

        i= 0
        self.poly.xy = np.array(
            list(self.poly.xy[:i+1]) +
            [(xdpos, ydpos)] +
            list(self.poly.xy[i+1:]))
        self._update_line()
        return i+1

    def key_press_callback(self, event):
        'whenever a key is pressed'
        if not event.inaxes:
            return
        else:
            self.doActionForKeyEvent(event)

    def motion_notify_callback(self, event):
        'on mouse movement'
        if event.inaxes is None:
            self.last_pos = None
            return
        self.last_pos = (event.x, event.y, event.xdata, event.ydata)
        ignore = (event.button not in self.buttons_t) or \
                 self.poly is None or self._ind is None
        if ignore:
            return
        x,y = event.xdata, event.ydata

        if self._ind == 0 or self._ind == self.last_vert_ind:
            self.poly.xy[0] = x,y
            self.poly.xy[self.last_vert_ind] = x,y
        else:
            self.poly.xy[self._ind] = x,y
        self._update_line()

        self.canvas.restore_region(self.background)
        self.ax.draw_artist(self.poly)
        self.ax.draw_artist(self.line)
        self.canvas.blit(self.ax.bbox)

    def _update_line(self):
        # save verts because polygon gets deleted when figure is closed
        if self.poly.xy.shape[0] == 1 or np.sum((self.poly.xy[0,:] - self.poly.xy[-1:,])**2) > 0:
            self.poly.xy = np.vstack((self.poly.xy, self.poly.xy[0,:]))
        self.verts = self.poly.xy
        self.last_vert_ind = len(self.poly.xy) - 1
        self.line.set_data(zip(*self.poly.xy))

    def get_ind_under_cursor(self, event):
        'get the index of the vertex under cursor if within max_ds tolerance'
        # display coords
        if event is None:
            if self.last_pos is None:
                return
            else:
                xpos, ypos, xdpos, ydpos = self.last_pos
        else:
            xpos, ypos = (event.x, event.y)

        if self.poly is None:
            ind = self.do_add(event)
            if ind is not None:
                self.canvas.draw()
                return
            
        xy = np.asarray(self.poly.xy)
        xyt = self.poly.get_transform().transform(xy)
        xt, yt = xyt[:, 0], xyt[:, 1]
        d = np.sqrt((xt - xpos)**2 + (yt - ypos)**2)
        indseq = np.nonzero(np.equal(d, np.amin(d)))[0]
        ind = indseq[0]
        if d[ind] >= self.max_ds:
            ind = self.do_add(event)
            if ind is not None:
                self.canvas.draw()
        return ind
