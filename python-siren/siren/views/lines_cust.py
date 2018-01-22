from __future__ import division, print_function

import warnings
import pdb
import numpy as np

from matplotlib.cbook import iterable, is_string_like, is_numlike, ls_mapper
from matplotlib.artist import allow_rasterization
from matplotlib.lines import Line2D

def segment_hits(cx, cy, x, y, radius):
    """
    Determine if any line segments are within radius of a
    point. Returns the list of line segments that are within that
    radius.
    """
    # Process single points specially
    if len(x) < 2:
        res, = np.nonzero((cx - x) ** 2 + (cy - y) ** 2 <= radius ** 2)
        return res

    # We need to lop the last element off a lot.
    xr, yr = x[:-1], y[:-1]

    # Only look at line segments whose nearest point to C on the line
    # lies within the segment.
    dx, dy = x[1:] - xr, y[1:] - yr
    Lnorm_sq = dx ** 2 + dy ** 2  # Possibly want to eliminate Lnorm==0
    u = ((cx - xr) * dx + (cy - yr) * dy) / Lnorm_sq
    candidates = (u >= 0) & (u <= 1)
    #if any(candidates): print "candidates",xr[candidates]

    # Note that there is a little area near one side of each point
    # which will be near neither segment, and another which will
    # be near both, depending on the angle of the lines.  The
    # following radius test eliminates these ambiguities.
    point_hits = (cx - x) ** 2 + (cy - y) ** 2 <= radius ** 2
    #if any(point_hits): print "points",xr[candidates]
    candidates = candidates & ~(point_hits[:-1] | point_hits[1:])

    # For those candidates which remain, determine how far they lie away
    # from the line.
    px, py = xr + u * dx, yr + u * dy
    line_hits = (cx - px) ** 2 + (cy - py) ** 2 <= radius ** 2
    #if any(line_hits): print "lines",xr[candidates]
    line_hits = line_hits & candidates
    points, = point_hits.ravel().nonzero()
    lines, = line_hits.ravel().nonzero()
    #print points,lines
    return np.concatenate((points, lines))


class CustLine2D(Line2D):
    """
    Derived from Line2D but applies data transform to the marker

    """

    @allow_rasterization
    def draw(self, renderer):
        """draw the Line with `renderer` unless visiblity is False"""
        if not self.get_visible():
            return

        if self._invalidy or self._invalidx:
            self.recache()
        self.ind_offset = 0  # Needed for contains() method.
        if self._subslice and self.axes:
            # Need to handle monotonically decreasing case also...
            x0, x1 = self.axes.get_xbound()
            i0, = self._x.searchsorted([x0], 'left')
            i1, = self._x.searchsorted([x1], 'right')
            subslice = slice(max(i0 - 1, 0), i1 + 1)
            self.ind_offset = subslice.start
            self._transform_path(subslice)

        transf_path = self._get_transformed_path()

        renderer.open_group('line2d', self.get_gid())
        gc = renderer.new_gc()
        self._set_gc_clip(gc)

        ln_color_rgba = self._get_rgba_ln_color()
        gc.set_foreground(ln_color_rgba)
        gc.set_alpha(ln_color_rgba[3])

        gc.set_antialiased(self._antialiased)
        gc.set_linewidth(self._linewidth)

        if self.is_dashed():
            cap = self._dashcapstyle
            join = self._dashjoinstyle
        else:
            cap = self._solidcapstyle
            join = self._solidjoinstyle
        gc.set_joinstyle(join)
        gc.set_capstyle(cap)
        gc.set_snap(self.get_snap())
        if self.get_sketch_params() is not None:
            gc.set_sketch_params(*self.get_sketch_params())

        funcname = self._lineStyles.get(self._linestyle, '_draw_nothing')
        if funcname != '_draw_nothing':
            tpath, affine = transf_path.get_transformed_path_and_affine()
            if len(tpath.vertices):
                self._lineFunc = getattr(self, funcname)
                funcname = self.drawStyles.get(self._drawstyle, '_draw_lines')
                drawFunc = getattr(self, funcname)

                if self.get_path_effects() and self._linewidth:
                    affine_frozen = affine.frozen()
                    for pe in self.get_path_effects():
                        pe_renderer = pe.get_proxy_renderer(renderer)
                        drawFunc(pe_renderer, gc, tpath, affine_frozen)
                else:
                    drawFunc(renderer, gc, tpath, affine.frozen())

        if self._marker:
            gc = renderer.new_gc()
            self._set_gc_clip(gc)
            rgbaFace = self._get_rgba_face()
            rgbaFaceAlt = self._get_rgba_face(alt=True)
            edgecolor = self.get_markeredgecolor()
            if is_string_like(edgecolor) and edgecolor.lower() == 'none':
                gc.set_linewidth(0)
                gc.set_foreground(rgbaFace)
            else:
                gc.set_foreground(edgecolor)
                gc.set_linewidth(self._markeredgewidth)

            marker = self._marker
            tpath, affine = transf_path.get_transformed_points_and_affine()
            if len(tpath.vertices):
                # subsample the markers if markevery is not None
                markevery = self.get_markevery()
                if markevery is not None:
                    if iterable(markevery):
                        startind, stride = markevery
                    else:
                        startind, stride = 0, markevery
                    if tpath.codes is not None:
                        codes = tpath.codes[startind::stride]
                    else:
                        codes = None
                    vertices = tpath.vertices[startind::stride]
                    subsampled = Path(vertices, codes)
                else:
                    subsampled = tpath

                snap = marker.get_snap_threshold()
                if type(snap) == float:
                    snap = renderer.points_to_pixels(self._markersize) >= snap
                gc.set_snap(snap)
                gc.set_joinstyle(marker.get_joinstyle())
                gc.set_capstyle(marker.get_capstyle())
                marker_path = marker.get_path()
                marker_trans = marker.get_transform()
                w = renderer.points_to_pixels(self._markersize)
                if marker.get_marker() != ',':
                    # Don't scale for pixels, and don't stroke them
                    # pass
                    marker_trans = marker_trans.scale(w)
                else:
                    gc.set_linewidth(0)
                if rgbaFace is not None:
                    gc.set_alpha(rgbaFace[3])

                if self.get_path_effects():
                    affine_frozen = affine.frozen()
                    for pe in self.get_path_effects():
                        pe.draw_markers(renderer, gc, marker_path,
                                        marker_trans, subsampled,
                                        affine_frozen, rgbaFace)
                else:
                    ##### EDITED
                    tmp = affine.get_matrix()
                    marker_trans.set_matrix(tmp)
                    marker_trans.translate(-tmp[0,2], -tmp[1,2])
                    renderer.draw_markers(gc, marker_path, marker_trans,
                                          subsampled, affine.frozen(),
                                          rgbaFace)


                alt_marker_path = marker.get_alt_path()
                if alt_marker_path:
                    if rgbaFaceAlt is not None:
                        gc.set_alpha(rgbaFaceAlt[3])
                    alt_marker_trans = marker.get_alt_transform()
                    alt_marker_trans = alt_marker_trans.scale(w)

                    if self.get_path_effects():
                        affine_frozen = affine.frozen()
                        for pe in self.get_path_effects():
                            pe.draw_markers(renderer, gc, alt_marker_path,
                                            alt_marker_trans, subsampled,
                                            affine_frozen, rgbaFaceAlt)
                    else:
                        renderer.draw_markers(
                            gc, alt_marker_path, alt_marker_trans, subsampled,
                            affine.frozen(), rgbaFaceAlt)

            gc.restore()

        gc.restore()
        renderer.close_group('line2d')

    def contains(self, mouseevent):
        """
        Test whether the mouse event occurred on the line.  The pick
        radius determines the precision of the location test (usually
        within five points of the value).  Use
        :meth:`~matplotlib.lines.Line2D.get_pickradius` or
        :meth:`~matplotlib.lines.Line2D.set_pickradius` to view or
        modify it.

        Returns *True* if any values are within the radius along with
        ``{'ind': pointlist}``, where *pointlist* is the set of points
        within the radius.

        TODO: sort returned indices by distance
        """
        if callable(self._contains):
            return self._contains(self, mouseevent)

        if not is_numlike(self.pickradius):
            raise ValueError("pick radius should be a distance")

        # Make sure we have data to plot
        if self._invalidy or self._invalidx:
            self.recache()
        if len(self._xy) == 0:
            return False, {}

        # Convert points to pixels
        transformed_path = self._get_transformed_path()
        path, affine = transformed_path.get_transformed_path_and_affine()
        # path = affine.transform_path(path)
        # xy = path.vertices
        # xt = self._xy[:, 0]
        # yt = self._xy[:, 1]

        mev_xy = affine.inverted().transform([(mouseevent.x, mouseevent.y)])[0]
        ind, = np.where(self._marker.get_path().contains_points((mev_xy-self._xy)))
        return len(ind) > 0, dict(ind=ind)
