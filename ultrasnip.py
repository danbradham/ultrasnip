#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import sys
from math import ceil, sqrt
from Qt import QtWidgets, QtCore, QtGui

__version__ = '0.1.1'
__title__ = 'UltraSnip'
__author__ = 'Dan Bradham'
__license__ = 'MIT'
__email__ = 'danielbradham@gmail.com'
__url__ = 'https://github.com/danbradham/ultrasnip'
version_info = tuple([int(x) for x in __version__.split('.')])


class UltraSnip(QtWidgets.QDialog):
    '''The main UltraSnip Dialog. This class is used to select a section of
    your desktop. This dialog is implemented as a single widget with a custom
    paint method. Custom Widget and Manipulator classes are implemented to
    handle manipulation and painting of their respective portion of the UI.

    Arguments:
        region (QtCore.QRect)- Optional starting region
        font (QtGui.QFont) - Optional font
        colors (dict) - Dict of QtGui.QColor objects for theming
        parent (QWidget) - Parent QWidget
    '''

    def __init__(self, region=None, font=None, colors=None, parent=None):
        super(UltraSnip, self).__init__(parent)
        app = QtWidgets.QApplication.instance()
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Window
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        desktop_region = app.primaryScreen().virtualGeometry()
        self.setGeometry(desktop_region)

        # Initialize Colors
        self.theme = Theme(font=font, **(colors or {}))

        # Initialize Internals
        self.region = region or QtCore.QRect()
        self.selection = region is not None
        self.origin = None
        self.pixmap = None
        self.has_zoom_manipulators = False
        self.selecting = False
        self.manipulating = False

        self.widgets = WidgetGroup(
            MoveManipulator(self),
            SideManipulator(self, 'left'),
            CornerManipulator(self, 'topLeft'),
            SideManipulator(self, 'top'),
            CornerManipulator(self, 'topRight'),
            SideManipulator(self, 'right'),
            CornerManipulator(self, 'bottomRight'),
            SideManipulator(self, 'bottom'),
            CornerManipulator(self, 'bottomLeft'),
        )
        self.grab_desktop()

    def grab_desktop(self):
        '''Grab the current virtual desktop.'''

        app = QtWidgets.QApplication.instance()
        region = app.primaryScreen().virtualGeometry()
        pixmap = app.primaryScreen().grabWindow(
            app.desktop().winId(),
            region.x(),
            region.y(),
            region.width(),
            region.height()
        )
        self.pixmap = pixmap
        self.update_zoom_manipulators(pixmap)

    def update_zoom_manipulators(self, pixmap):
        '''Create or update the zoom manipulators based on the input pixmap.'''

        if self.has_zoom_manipulators:
            for w in self.widgets.widgets:
                if isinstance(w, ZoomManipulator):
                    w.set_pixmap(pixmap)
            return

        margin = self.theme.margins
        boxsize = px(100)
        box = QtCore.QRect(0, 0, boxsize, boxsize)
        x = lambda i: (margin * (i + 1)) + (boxsize * 0.5) + (boxsize * i)
        y = margin + boxsize * 0.5
        self.widgets.extend([
            ZoomManipulator(
                self,
                pixmap,
                'topLeft',
                QtCore.QPoint(x(0), y),
                box,
            ),
            ZoomManipulator(
                self,
                pixmap,
                'topRight',
                QtCore.QPoint(x(1), y),
                box,
            ),
            ZoomManipulator(
                self,
                pixmap,
                'bottomRight',
                QtCore.QPoint(x(2), y),
                box,
            ),
            ZoomManipulator(
                self,
                pixmap,
                'bottomLeft',
                QtCore.QPoint(x(3), y),
                box,
            ),
        ])
        self.has_zoom_manipulators = True

    @property
    def global_region(self):
        if not self.selection:
            return
        rect = QtCore.QRect(self.region)
        rect.moveTopLeft(self.mapToGlobal(self.region.topLeft()))
        return rect

    def mousePressEvent(self, event):
        pos = event.pos()
        self.origin = pos
        left = event.button() == QtCore.Qt.LeftButton
        if left:
            widget = self.widgets.select_at_pos(pos)
            if widget:
                widget.press(pos)
                self.manipulating = True
            else:
                self.selecting = True
                self.selection = True

            self.update()

    def mouseMoveEvent(self, event):
        if self.selecting:
            self.region = QtCore.QRect(self.origin, event.pos()).normalized()

        if self.selection:
            if self.manipulating:
                self.widgets.active.drag(event.pos())
            else:
                self.widgets.hover_at_pos(event.pos())

        self.update()

    def mouseReleaseEvent(self, event):
        self.origin = None
        self.selecting = False
        self.manipulating = False
        self.widgets.release(event.pos())

    def keyPressEvent(self, event):
        # Escape - close
        if event.key() == QtCore.Qt.Key_Escape:
            self.reject()
            return

        # Enter - grab screen accept
        elif event.key() == QtCore.Qt.Key_Return:
            self.accept()
            return

        # Tab - cycle through manipulator selection
        elif event.key() == QtCore.Qt.Key_Tab:
            self.widgets.select_next()
        elif event.key() == QtCore.Qt.Key_Backtab:
            self.widgets.select_prev()

        # Arrow Keys - move active handle
        elif event.key() == QtCore.Qt.Key_Left:
            self.widgets.key_left()
        elif event.key() == QtCore.Qt.Key_Right:
            self.widgets.key_right()
        elif event.key() == QtCore.Qt.Key_Up:
            self.widgets.key_up()
        elif event.key() == QtCore.Qt.Key_Down:
            self.widgets.key_down()

        self.update()
        event.accept()

    def focusOutEvent(self, event):
        self.close()
        event.accept()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(painter.Antialiasing)

        # Paint background
        painter.fillRect(self.rect(), self.theme.fill('background'))
        if self.selection:
            painter.setCompositionMode(painter.CompositionMode_Clear)
            painter.fillRect(self.region, self.theme.fill('empty'))
            painter.setCompositionMode(painter.CompositionMode_SourceOver)
            painter.fillRect(self.region, self.theme.fill('foreground'))

            # Paint widgets
            self.widgets.paint(painter)

        painter.end()


class Theme(object):
    '''Theme object handles colors, pens, brushes, and fonts.'''

    default_colors = dict(
        active=QtGui.QColor(255, 55, 115, 255),
        inactive=QtGui.QColor(153, 33, 93, 255),
        hover=QtGui.QColor(204, 44, 124, 255),
        white=QtGui.QColor(255, 255, 255, 255),
        black=QtGui.QColor(0, 0, 0, 255),
        empty=QtGui.QColor(255, 255, 255, 0),
        foreground=QtGui.QColor(255, 255, 255, 1),
        background=QtGui.QColor(255, 55, 115, 50),
    )
    default_font = QtGui.QFont('Sans Serif', 10, 50)

    def __init__(self, margins=None, font=None, **colors):
        self.margins = margins or px(20)
        self._font = font or self.default_font
        self.colors = dict(self.default_colors, **colors)

    def solid(self, color='white', width=1):
        return QtGui.QPen(self.colors[color], width, QtCore.Qt.SolidLine)

    def dotted(self, color='white', width=1):
        return QtGui.QPen(self.colors[color], width, QtCore.Qt.DotLine)

    def fill(self, color='active'):
        return QtGui.QBrush(self.colors[color])

    def font(self, family='Sans Serif', size=-1, weight=-1):
        if family == 'Sans Serif' and size < 0 and weight < 0:
            return self._font
        return QtGui.QFont(family, size, weight)

    def text_width(self, font, text):
        return QtGui.QFontMetrics(font).boundingRect(text).width()

    def text_height(self, font, text):
        return QtGui.QFontMetrics(font).boundingRect(text).height()


def precision():
    '''Returns the current manipulation precision based on key modifiers.'''

    modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
    if modifiers & QtCore.Qt.ShiftModifier:
        return 10
    if modifiers & QtCore.Qt.ControlModifier:
        return 50
    return 1


class WidgetGroup(object):
    '''A List of Widgets used to maintain all interactions between a
    parent widget and this list of widgets.'''

    def __init__(self, *widgets):
        self.widgets = list(widgets)
        self.active = None
        self.active_idx = 0
        self.hovering = None

    def extend(self, widgets):
        for w in widgets:
            self.append(w)

    def append(self, widget):
        if not isinstance(widget, Widget):
            raise ValueError('widget expected got %s' % type(widget))
        if widget in self.widgets:
            return
        self.widgets.append(widget)

    def remove(self, widget):
        self.widgets.remove(widget)

    def insert(self, index, widget):
        if not isinstance(widget, Widget):
            raise ValueError('widget expected got %s' % type(widget))
        if widget in self.widgets:
            return
        self.widgets.insert(index, widget)

    def hit(self, widget, pos):
        return widget.bounds().contains(pos)

    def key_up(self):
        if self.active:
            self.active.key_up()

    def key_down(self):
        if self.active:
            self.active.key_down()

    def key_left(self):
        if self.active:
            self.active.key_left()

    def key_right(self):
        if self.active:
            self.active.key_right()

    def press(self, pos):
        if self.active:
            self.active.press(pos)

    def release(self, pos):
        if self.active:
            self.active.release(pos)

    def select_next(self):
        if not self.active:
            self.select(self.widgets[0])
        elif self.active == self.widgets[-1]:
            self.clear_selection()
        else:
            self.select(self.widgets[self.widgets.index(self.active) + 1])

    def select_prev(self):
        if not self.active:
            self.select(self.widgets[-1])
        elif self.active == self.widgets[0]:
            self.clear_selection()
        else:
            self.select(self.widgets[self.widgets.index(self.active) - 1])

    def clear_selection(self):
        self.active = None
        for widget in self.widgets:
            widget.active = False

    def select(self, widget):
        self.clear_selection()
        self.active = widget
        self.active_idx = self.widgets.index(widget)
        widget.active = True

    def select_at_pos(self, pos):
        self.clear_selection()
        for widget in self.widgets:
            if self.hit(widget, pos):
                widget.active = True
                self.active = widget
                return widget

    def clear_hovering(self):
        self.hovering = None
        for widget in self.widgets:
            widget.hovering = False

    def hover(self, widget):
        self.clear_hovering()
        self.hover = widget
        widget.hover = True

    def hover_at_pos(self, pos):
        self.clear_hovering()
        for widget in self.widgets:
            if self.hit(widget, pos):
                widget.hovering = True
                self.hovering = widget
                return widget

    def paint(self, painter):
        for widget in self.widgets:
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(QtCore.Qt.NoPen)
            widget.paint(painter)


class Widget(QtCore.QObject):
    '''Base class for all widgets.'''

    clicked = QtCore.Signal()
    pressed = QtCore.Signal()
    released = QtCore.Signal()
    toggled = QtCore.Signal(bool)

    def __init__(self, parent):
        super(Widget, self).__init__(parent)
        self.parent = parent
        self.theme = parent.theme
        self.active = False
        self.hovering = False
        self.enabled = True
        self.checked = False
        self.checkable = False
        self.drag_source = QtCore.QPoint()
        self.drag_offset = QtCore.QPoint()

    @property
    def pos(self):
        return NotImplemented

    @property
    def canvas(self):
        return self.parent.rect()

    @property
    def region(self):
        return self.parent.region

    @region.setter
    def region(self, rect):
        self.parent.region = rect

    def limit(self, x, y):
        return (
            clip(x, 0, self.canvas.width()),
            clip(y, 0, self.canvas.height()),
        )

    def limit_center(self, x, y):
        min_x = ceil(self.region.width() * 0.5)
        max_x = self.canvas.width() - min_x
        min_y = ceil(self.region.height() * 0.5)
        max_y = self.canvas.height() - min_y
        return clip(x, min_x, max_x), clip(y, min_y, max_y)

    def normalize_region(self):
        self.region = self.region.normalized()

    def move(self, x, y):
        return NotImplemented

    def set(self, x, y):
        return NotImplemented

    def key_left(self):
        return NotImplemented

    def key_right(self):
        return NotImplemented

    def key_up(self):
        return NotImplemented

    def key_down(self):
        return NotImplemented

    def press(self, pos):
        self.pressed.emit()
        self.drag_source = pos
        self.drag_offset = self.pos - pos
        self.clicked.emit()

    def drag(self, pos):
        pos += self.drag_offset
        self.set(pos.x(), pos.y())

    def release(self, pos):
        self.released.emit()
        self.drag_source = QtCore.QPoint()
        self.drag_offset = QtCore.QPoint()
        if self.checkable:
            self.checked = not self.checked
            self.toggled.emit(self.checked)

    def bounds(self):
        return NotImplemented

    def paint(self, painter):
        return NotImplemented


class Manipulator(Widget):
    '''Base class for all manipulators.'''

    def key_left(self):
        self.move(-1 * precision(), 0)

    def key_right(self):
        self.move(1 * precision(), 0)

    def key_up(self):
        self.move(0, -1 * precision())

    def key_down(self):
        self.move(0, 1 * precision())


class ZoomManipulator(Manipulator):
    '''Zoom manipulator widget.

    An enlarged view of one corner of a rect. Adjusts the location of
    the corner of the rect when arrow keys are pressed.
    '''

    def __init__(self, parent, pixmap, corner, pos, rect):
        super(ZoomManipulator, self).__init__(parent)
        self.corner = corner
        self._pixmap = pixmap
        self._pos = pos
        self._rect = rect
        self._corner_pos = None
        self._pixmap_cropped = None

    def set_pixmap(self, pixmap):
        self._pixmap_cropped = None
        self._pixmap = pixmap

    @property
    def pixmap(self):
        if (
            not self._pixmap_cropped or
            self.corner_pos_corrected != self._corner_pos
        ):
            self._corner_pos = self.corner_pos_corrected
            self._pixmap_cropped = self._pixmap.copy(self.corner_rect)
        return self._pixmap_cropped.scaled(100, 100)

    @property
    def corner_pos_corrected(self):
        '''Corner position corrected for borders - fixes zoom previews.'''
        pos = getattr(self.parent.region, self.corner)()
        if self.corner == 'topLeft':
            pos += QtCore.QPoint(-1, -1)
        elif self.corner == 'topRight':
            pos += QtCore.QPoint(0, -1)
        elif self.corner == 'bottomLeft':
            pos += QtCore.QPoint(-1, 0)
        return pos

    @property
    def corner_pos(self):
        '''Corner position of parent region.'''
        return getattr(self.parent.region, self.corner)()

    @property
    def corner_rect(self):
        '''Rect around corner position of parent region.'''
        rect = QtCore.QRect(0, 0, 10, 10)
        rect.moveCenter(QtCore.QPoint(self.corner_pos_corrected))
        return rect

    @property
    def pos(self):
        return self._pos

    def move(self, x, y):
        self.set(self.corner_pos.x() + x, self.corner_pos.y() + y)

    def set(self, x, y):
        x, y = self.limit(x, y)
        method = 'set' + self.corner[0].upper() + self.corner[1:]
        set_ = getattr(self.region, method)
        set_(QtCore.QPoint(x, y))
        self.normalize_region()

    def bounds(self):
        rect = QtCore.QRect(
            0,
            0,
            self._rect.width() + self.theme.margins,
            self._rect.width() + self.theme.margins,
        )
        rect.moveCenter(self.pos)
        return rect

    def get_lines(self, box):
        center = box.center()
        right = box.right()
        top = box.top()
        left = box.left()
        bottom = box.bottom()
        if self.corner == 'topLeft':
            return [
                QtCore.QLine(center, QtCore.QPoint(right, center.y())),
                QtCore.QLine(center, QtCore.QPoint(center.x(), bottom))
            ]
        if self.corner == 'topRight':
            return [
                QtCore.QLine(center, QtCore.QPoint(left, center.y())),
                QtCore.QLine(center, QtCore.QPoint(center.x(), bottom))
            ]
        if self.corner == 'bottomRight':
            return [
                QtCore.QLine(center, QtCore.QPoint(left, center.y())),
                QtCore.QLine(center, QtCore.QPoint(center.x(), top))
            ]
        if self.corner == 'bottomLeft':
            return [
                QtCore.QLine(center, QtCore.QPoint(right, center.y())),
                QtCore.QLine(center, QtCore.QPoint(center.x(), top))
            ]

    def get_box(self):
        rect = QtCore.QRect(self._rect)
        rect.moveCenter(self.pos)
        return rect

    def paint(self, painter):
        box = self.get_box()
        lines = self.get_lines(box)
        painter.drawPixmap(box, self.pixmap)
        if self.active:
            painter.setPen(self.theme.solid('active'))
        elif self.hovering:
            painter.setPen(self.theme.solid('hover'))
        else:
            painter.setPen(self.theme.solid('inactive'))
        # Draw outline
        painter.drawRect(box)
        # Draw corner lines
        painter.drawLines(lines)


class CornerManipulator(Manipulator):
    '''Corner manipulator widget.

    Handle positioned relative one corner of a rect. Adjusts the location of
    the corner when mouse is dragged or arrow keys are pressed.
    '''

    def __init__(self, parent, corner='topLeft'):
        super(CornerManipulator, self).__init__(parent)
        self.corner = corner

    @property
    def pos(self):
        return getattr(self.parent.region, self.corner)()

    def move(self, x, y):
        self.set(self.pos.x() + x, self.pos.y() + y)

    def set(self, x, y):
        x, y = self.limit(x, y)
        method = 'set' + self.corner[0].upper() + self.corner[1:]
        set_ = getattr(self.region, method)
        set_(QtCore.QPoint(x, y))
        self.normalize_region()

    def bounds(self):
        rect = QtCore.QRect(0, 0, 22, 22)
        rect.moveCenter(self.pos)
        return rect

    def get_box(self):
        rect = QtCore.QRect(0, 0, 11, 11)
        rect.moveCenter(self.pos)
        return rect

    def paint(self, painter):
        box = self.get_box()
        if self.active:
            painter.fillRect(box, self.theme.fill('active'))
        elif self.hovering:
            painter.fillRect(box, self.theme.fill('hover'))
        else:
            # painter.fillRect(box, self.theme.fill('inactive'))
            pass


class SideManipulator(Manipulator):
    '''Side manipulator widget.

    Handle positioned relative one side of a rect. Adjusts the location of
    the side when mouse is dragged or arrow keys are pressed.
    '''

    def __init__(self, parent, side='top'):
        super(SideManipulator, self).__init__(parent)
        self.side = side

    @property
    def pos(self):
        coord = getattr(self.region, self.side)()
        if self.horizontal:
            return QtCore.QPoint(self.region.center().x(), coord)
        else:
            return QtCore.QPoint(coord, self.region.center().y())

    @property
    def horizontal(self):
        return self.side in ('top', 'bottom')

    @property
    def vertical(self):
        return self.side in ('left', 'right')

    @property
    def width(self):
        return (20, ceil(self.region.width() * 0.9))[self.horizontal]

    @property
    def height(self):
        return (20, ceil(self.region.height() * 0.9))[self.vertical]

    def xy_to_coord(self, x, y):
        return (x, y)[self.horizontal]

    def move(self, x, y):
        self.set(self.pos.x() + x, self.pos.y() + y)

    def set(self, x, y):
        x, y = self.limit(x, y)
        method = 'set' + self.side.title()
        set_ = getattr(self.region, method)
        set_(self.xy_to_coord(x, y))
        self.normalize_region()

    def bounds(self):
        if self.horizontal:
            rect = QtCore.QRect(0, 0, self.width, self.height * 2)
        else:
            rect = QtCore.QRect(0, 0, self.width * 2, self.height)
        rect.moveCenter(self.pos)
        return rect

    def get_line(self):
        if self.side == 'top':
            return self.region.topLeft(), self.region.topRight()
        elif self.side == 'right':
            return self.region.topRight(), self.region.bottomRight()
        elif self.side == 'bottom':
            return self.region.bottomLeft(), self.region.bottomRight()
        else:
            return self.region.topLeft(), self.region.bottomLeft()

    def get_box(self):
        if self.horizontal:
            width = ceil(self.width * 0.5)
            height = 10
        else:
            width = 10
            height = ceil(self.height * 0.5)

        rect = QtCore.QRect(0, 0, width, height)
        rect.moveCenter(self.pos)
        return rect

    def paint(self, painter):
        box = self.get_box()

        if self.active:
            painter.fillRect(box, self.theme.fill('active'))
        elif self.hovering:
            painter.fillRect(box, self.theme.fill('hover'))
        else:
            # painter.fillRect(box, self.theme.fill('inactive'))
            pass


class MoveManipulator(Manipulator):
    '''Move manipulator widget.

    Handle positioned relative to the input rect. Moves the input rect when
    dragged or when the arrow keys are pressed.
    '''


    alt_arrows = [
        QtGui.QPolygon.fromList([
            QtCore.QPoint(20, -10),
            QtCore.QPoint(40, -10),
            QtCore.QPoint(40, -18),
            QtCore.QPoint(60, 0),
            QtCore.QPoint(40, 18),
            QtCore.QPoint(40, 10),
            QtCore.QPoint(20, 10),
            QtCore.QPoint(20, -10),
        ]),
        QtGui.QPolygon.fromList([
            QtCore.QPoint(10, 20),
            QtCore.QPoint(10, 40),
            QtCore.QPoint(18, 40),
            QtCore.QPoint(0, 60),
            QtCore.QPoint(-18, 40),
            QtCore.QPoint(-10, 40),
            QtCore.QPoint(-10, 20),
            QtCore.QPoint(10, 20),
        ]),
        QtGui.QPolygon.fromList([
            QtCore.QPoint(-20, 10),
            QtCore.QPoint(-40, 10),
            QtCore.QPoint(-40, 18),
            QtCore.QPoint(-60, 0),
            QtCore.QPoint(-40, -18),
            QtCore.QPoint(-40, -10),
            QtCore.QPoint(-20, -10),
            QtCore.QPoint(-20, 10),
        ]),
        QtGui.QPolygon.fromList([
            QtCore.QPoint(-10, -20),
            QtCore.QPoint(-10, -40),
            QtCore.QPoint(-18, -40),
            QtCore.QPoint(0, -60),
            QtCore.QPoint(18, -40),
            QtCore.QPoint(10, -40),
            QtCore.QPoint(10, -20),
            QtCore.QPoint(-10, -20),
        ])
    ]

    arrows = [
        QtGui.QPolygon.fromList([
            QtCore.QPoint(40, -18),
            QtCore.QPoint(60, 0),
            QtCore.QPoint(40, 18),
        ]),
        QtGui.QPolygon.fromList([
            QtCore.QPoint(18, 40),
            QtCore.QPoint(0, 60),
            QtCore.QPoint(-18, 40),
        ]),
        QtGui.QPolygon.fromList([
            QtCore.QPoint(-40, 18),
            QtCore.QPoint(-60, 0),
            QtCore.QPoint(-40, -18),
        ]),
        QtGui.QPolygon.fromList([
            QtCore.QPoint(-18, -40),
            QtCore.QPoint(0, -60),
            QtCore.QPoint(18, -40),
        ]),
    ]

    @property
    def pos(self):
        return self.region.center()

    def get_arrows(self):
        center = self.parent.region.center()
        xform = QtGui.QTransform()
        xform.translate(center.x(), center.y())
        arrows = []
        for arrow in self.arrows:
            moved_arrow = xform.map(arrow)
            if not self.parent.region.contains(moved_arrow.boundingRect()):
                N = normalize(arrow[1])
                if N.x():
                    N *= self.parent.region.width() * 0.5
                else:
                    N *= self.parent.region.height() * 0.5
                cform = QtGui.QTransform()
                cform.translate(N.x(), N.y())
                moved_arrow = cform.map(moved_arrow)
            arrows.append(moved_arrow)
        return arrows

    @property
    def width(self):
        return ceil(self.region.width() * 0.9)

    @property
    def height(self):
        return ceil(self.region.height() * 0.9)

    def move(self, x, y):
        self.set(self.pos.x() + x, self.pos.y() + y)

    def set(self, x, y):
        x, y = self.limit_center(x, y)
        self.region.moveCenter(QtCore.QPoint(x, y))
        self.normalize_region()

    def bounds(self):
        rect = QtCore.QRect(0, 0, self.width, self.height)
        rect.moveCenter(self.region.center())
        return rect

    def paint(self, painter):
        painter.setPen(QtCore.Qt.NoPen)
        if self.active:
            painter.setBrush(self.theme.fill('active'))
            for arrow in self.get_arrows():
                painter.drawPolygon(arrow)

            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(self.theme.solid('active'))
            painter.drawRect(self.region)
        elif self.hovering:
            painter.setBrush(self.theme.fill('hover'))
            for arrow in self.get_arrows():
                painter.drawPolygon(arrow)

            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(self.theme.solid('hover'))
            painter.drawRect(self.region)
        else:
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(self.theme.solid('inactive'))
            painter.drawRect(self.region)


class Text(Widget):
    '''A Text widget.

    Text
    '''


    def __init__(self, parent, text, pos):
        super(Text, self).__init__(parent)
        self.text = text
        self.font = self.theme.font(size=16, weight=75)
        self._pos = pos

    @property
    def pos(self):
        height = self.theme.text_height(self.font, self.text)
        return QtCore.QPoint(self._pos.x(), self._pos.y() + height)

    def bounds(self):
        return QtCore.QRect(-1, -1, 1, 1)

    def paint(self, painter):
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(self.theme.solid('active'))
        painter.setFont(self.font)
        painter.drawText(self.pos, self.text)


class Button(Widget):
    '''A Button widget.

    | button |
    '''


    def __init__(self, parent, text, pos):
        super(Button, self).__init__(parent)
        self.text = text
        self.font = self.theme.font(size=16, weight=50)
        self._pos = pos

    @property
    def pos(self):
        height = self.theme.text_height(self.font, self.text)
        height += self.theme.margins
        return QtCore.QPoint(self._pos.x(), self._pos.y() + height)

    def get_box(self):
        height = self.theme.text_height(self.font, self.text)
        height += self.theme.margins
        width = self.theme.text_width(self.font, self.text)
        width += self.theme.margins * 2
        return QtCore.QRect(self.pos.x(), self.pos.y(), width, height)

    def bounds(self):
        return self.get_box()

    def paint(self, painter):
        box = self.get_box()
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(self.theme.solid('active'))
        painter.setFont(self.font)
        painter.drawText(box, QtCore.Qt.AlignCenter, self.text)
        painter.drawRect(box)


class Options(Widget):
    '''An Options widget.

    < | option | >
    '''

    arrows = [
        QtGui.QPolygon.fromList([
            QtCore.QPoint(-10, 18),
            QtCore.QPoint(-30, 0),
            QtCore.QPoint(-10, -18),
        ]),
        QtGui.QPolygon.fromList([
            QtCore.QPoint(10, -18),
            QtCore.QPoint(30, 0),
            QtCore.QPoint(10, 18),
        ]),
    ]
    optionChanged = QtCore.Signal(int)

    def __init__(self, parent, default_text, options, width, pos):
        super(Options, self).__init__(parent)
        self.default_text = default_text
        self.width = width
        self.text = default_text
        if options[0] is not None:
            options.insert(0, None)
        self.options = options
        self.option = 0
        self.font = self.theme.font(size=16, weight=50)
        self._pos = pos

    def key_left(self):
        next_option = self.option - 1
        if 0 <= next_option:
            self.option = next_option
            self.optionChanged = QtCore.Signal(int)
        self.text_from_option(self.option)

    def key_right(self):
        next_option = self.option + 1
        if next_option < len(self.options):
            self.option = next_option
            self.optionChanged = QtCore.Signal(int)
        self.text_from_option(self.option)

    def text_from_option(self, option):
        if option == 0:
            self.text = self.default_text
        else:
            size = self.options[option]
            self.text = '%sx%s' % (size.width(), size.height())

    def press(self, pos):
        super(Options, self).press(pos)
        left, right = self.get_arrows()
        if left.boundingRect().contains(pos):
            self.key_left()
        if right.boundingRect().contains(pos):
            self.key_right()

    @property
    def pos(self):
        height = self.theme.text_height(self.font, self.default_text)
        height += self.theme.margins
        return QtCore.QPoint(self._pos.x() + 52, self._pos.y())

    def get_arrows(self):
        box = self.get_box()
        left = QtGui.QTransform()
        left.translate(box.left(), box.center().y())
        right = QtGui.QTransform()
        right.translate(box.right(), box.center().y())
        return [left.map(self.arrows[0]), right.map(self.arrows[1])]

    def get_box(self):
        height = self.theme.text_height(self.font, self.default_text)
        height += self.theme.margins
        return QtCore.QRect(self.pos.x(), self.pos.y(), self.width, height)

    def bounds(self):
        box = self.get_box()
        box.setLeft(box.left() - 40)
        box.setRight(box.right() + 40)
        return box

    def paint(self, painter):
        box = self.get_box()
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setFont(self.font)
        if self.active:
            painter.setPen(self.theme.solid('active'))
        elif self.hovering:
            painter.setPen(self.theme.solid('hover'))
        else:
            painter.setPen(self.theme.solid('inactive'))

        painter.drawText(box, QtCore.Qt.AlignCenter, self.text)
        painter.drawRect(box)

        if self.active:
            painter.setBrush(self.theme.fill('active'))
        elif self.hovering:
            painter.setBrush(self.theme.fill('hover'))
        else:
            painter.setBrush(self.theme.fill('inactive'))
        for arrow in self.get_arrows():
            painter.drawPolygon(arrow)


class Confirm(QtWidgets.QDialog):
    '''A dead simple confirmation dialog that displays a pixmap.'''

    def __init__(self, pixmap, title, reject, accept, parent=None):
        super(Confirm, self).__init__(parent)
        self.pixmap = pixmap

        self.button_yes = QtWidgets.QPushButton(accept, self)
        self.button_yes.clicked.connect(self.accept)
        self.button_no = QtWidgets.QPushButton(reject, self)
        self.button_no.clicked.connect(self.reject)
        self.label_img = QtWidgets.QLabel(self)
        self.label_img.setPixmap(self.pixmap)

        self.layout_buttons = QtWidgets.QHBoxLayout()
        self.layout_buttons.setAlignment(QtCore.Qt.AlignRight)
        self.layout_buttons.addWidget(self.button_no)
        self.layout_buttons.addWidget(self.button_yes)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.label_img)
        self.layout.addLayout(self.layout_buttons)

        self.setLayout(self.layout)
        self.setWindowTitle(title)


# Helper functions

def clip(value, minimum, maximum):
    return min(max(minimum, value), maximum)


def normalize(qpoint):
    length = sqrt((qpoint.x() * qpoint.x()) + (qpoint.y() * qpoint.y()))
    return QtCore.QPoint(qpoint.x() / length, qpoint.y() / length)


# DPI Aware scaling #

def dpi():
    '''Get screen DPI to scale UI independent of monitor size.'''
    return float(get_event_loop().desktop().logicalDpiX())


def factor():
    '''Get UI scale factor'''
    return dpi() / 96.0


def px(value):
    '''Scale a pixel value based on screen dpi.'''
    return int(factor() * value)


# Functional API #

class EventLoop(object):
    '''Simply stores a reference to the current QApplication instance.'''

    standalone = False
    instance = None


def get_event_loop():
    '''Get the QApplication event loop.'''

    if EventLoop.instance:
        return EventLoop.instance

    qapp = QtWidgets.QApplication.instance()
    if not qapp:
        EventLoop.standalone = True
        qapp = QtWidgets.QApplication([])

    EventLoop.instance = qapp


def confirm(pixmap, title='Confirm?', reject='Cancel', accept='Accept'):
    '''Preview and confirm a pixmap in a dialog.

    Arguments:
        pixmap (QtGui.QPixmap) - The pixmap to preview for confirmation.
        title (str) - Window title.
        reject (str) - Reject button text.
        accept (str) - Accept button text.
    Returns:
        True or False
    '''

    get_event_loop()
    return Confirm(pixmap, title, reject, accept).exec_()


def capture_region(region=None):
    '''Capture and a region of your desktop across all monitors.'''

    loop = get_event_loop()

    if region is None:
        region = loop.primaryScreen().virtualGeometry()

    pixmap = loop.primaryScreen().grabWindow(
        loop.desktop().winId(),
        region.x(),
        region.y(),
        region.width(),
        region.height()
    )
    return pixmap


def select(region=None, font=None, colors=None):
    '''Select a screen region using UltraSnip and return a QRect.

    Arguments:
        region (QtCore.QRect)- Optional starting region
        font (QtGui.QFont) - Optional font
        colors (dict) - Dict of QtGui.QColor objects for theming
    Returns:
        QtCore.QRect - QRect relative to desktops virtual geometry
    '''

    get_event_loop()
    snip = UltraSnip(region, font, colors)
    if snip.exec_():
        return snip.global_region


def select_and_capture(region=None, font=None, colors=None):
    '''Select a screen region using UltraSnip and return a pixmap.

    Arguments:
        region (QtCore.QRect)- Optional starting region
        font (QtGui.QFont) - Optional font
        colors (dict) - Dict of QtGui.QColor objects for theming
    Returns:
        QtGui.QPixmap - captured pixmap of selected desktop region
    '''

    region = select(region, font, colors)
    return capture_region(region)


def main():
    '''CLI interface'''

    import argparse
    parser = argparse.ArgumentParser(
        prog='UltraSnip',
        description='A desktop snipping tool written in Qt for Python.'
    )
    parser.add_argument(
        '--save',
        '-s',
        type=str,
        help='Path to save capture to for example: output.png',
    )
    parser.add_argument(
        '--measure',
        '-m',
        action='store_true',
        help='Output only the width and height of the region.',
    )
    parser.add_argument(
        '--confirm',
        '-c',
        action='store_true',
        help='Confirm the resulting pixmap using a simple dialog.',
    )

    args = parser.parse_args()

    region = select()
    if args.confirm:
        while not confirm(capture_region(region)):
            region = select(region)

    if region is None:
        sys.exit(1)

    if args.measure:
        print('%sx%s' % (region.width(), region.height()))

    pixmap = capture_region(region)
    if args.save:
        pixmap.save(args.save)
    elif args.measure:
        return
    else:
        from io import BytesIO
        byte_array = QtCore.QByteArray()
        buffer = QtCore.QBuffer(byte_array)
        buffer.open(QtCore.QIODevice.WriteOnly)
        pixmap.save(buffer, 'PNG')
        string_io = BytesIO(byte_array.data())
        string_io.seek(0)
        sys.stdout.buffer.write(string_io.read())
        sys.stdout.flush()

    sys.exit()


if __name__ == "__main__":
    main()
