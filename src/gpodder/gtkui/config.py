# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2018 The gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  gpodder.gtkui.config -- Config object with GTK+ support (2009-08-24)
#


from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango

import gpodder
from gpodder import util
from gpodder import config

_ = gpodder.gettext


class ConfigModel(Gtk.ListStore):
    C_NAME, C_TYPE_TEXT, C_VALUE_TEXT, C_TYPE, C_EDITABLE, C_FONT_STYLE, \
            C_IS_BOOLEAN, C_BOOLEAN_VALUE = list(range(8))

    def __init__(self, config):
        Gtk.ListStore.__init__(self, str, str, str, object, bool, int, bool, bool)

        self._config = config
        self._fill_model()

        self._config.add_observer(self._on_update)

    def _type_as_string(self, type):
        if type == int:
            return _('Integer')
        elif type == float:
            return _('Float')
        elif type == bool:
            return _('Boolean')
        else:
            return _('String')

    def _fill_model(self):
        self.clear()
        for key in sorted(self._config.all_keys()):
            # Ignore Gtk window state data (position, size, ...)
            if key.startswith('ui.gtk.state.'):
                continue

            value = self._config._lookup(key)
            fieldtype = type(value)

            style = Pango.Style.NORMAL
            #if value == default:
            #    style = Pango.Style.NORMAL
            #else:
            #    style = Pango.Style.ITALIC

            self.append((key, self._type_as_string(fieldtype),
                    config.config_value_to_string(value),
                    fieldtype, fieldtype is not bool, style,
                    fieldtype is bool, bool(value)))

    def _on_update(self, name, old_value, new_value):
        for row in self:
            if row[self.C_NAME] == name:
                style = Pango.Style.NORMAL
                #if new_value == self._config.Settings[name]:
                #    style = Pango.Style.NORMAL
                #else:
                #    style = Pango.Style.ITALIC
                new_value_text = config.config_value_to_string(new_value)
                self.set(row.iter, \
                        self.C_VALUE_TEXT, new_value_text,
                        self.C_BOOLEAN_VALUE, bool(new_value),
                        self.C_FONT_STYLE, style)
                break

    def stop_observing(self):
        self._config.remove_observer(self._on_update)


class UIConfig(config.Config):
    def __init__(self, filename='gpodder.conf'):
        config.Config.__init__(self, filename)
        self.__ignore_window_events = False

    def connect_gtk_editable(self, name, editable):
        editable.delete_text(0, -1)
        editable.insert_text(str(getattr(self, name)))

        def _editable_changed(editable):
            setattr(self, name, editable.get_chars(0, -1))
        editable.connect('changed', _editable_changed)

    def connect_gtk_spinbutton(self, name, spinbutton):
        current_value = getattr(self, name)

        adjustment = spinbutton.get_adjustment()
        if current_value > adjustment.get_upper():
            adjustment.set_upper(current_value)

        spinbutton.set_value(current_value)

        def _spinbutton_changed(spinbutton):
            setattr(self, name, spinbutton.get_value())
        spinbutton.connect('value-changed', _spinbutton_changed)

    def connect_gtk_paned(self, name, paned):
        paned.set_position(getattr(self, name))
        paned_child = paned.get_child1()

        def _child_size_allocate(x, y):
            setattr(self, name, paned.get_position())
        paned_child.connect('size-allocate', _child_size_allocate)

    def connect_gtk_togglebutton(self, name, togglebutton):
        togglebutton.set_active(getattr(self, name))

        def _togglebutton_toggled(togglebutton):
            setattr(self, name, togglebutton.get_active())
        togglebutton.connect('toggled', _togglebutton_toggled)

    def connect_gtk_window(self, window, config_prefix, show_window=False):
        cfg = getattr(self.ui.gtk.state, config_prefix)

        if gpodder.ui.win32:
            window.set_gravity(Gdk.GRAVITY_STATIC)

        window.resize(cfg.width, cfg.height)
        if cfg.x == -1 or cfg.y == -1:
            window.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        else:
            window.move(cfg.x, cfg.y)

        # Ignore events while we're connecting to the window
        self.__ignore_window_events = True

        def _receive_configure_event(widget, event):
            x_pos, y_pos = event.x, event.y
            width_size, height_size = event.width, event.height
            maximized = bool(event.window.get_state() & Gdk.WindowState.MAXIMIZED)
            if not self.__ignore_window_events and not maximized:
                cfg.x = x_pos
                cfg.y = y_pos
                cfg.width = width_size
                cfg.height = height_size

        window.connect('configure-event', _receive_configure_event)

        def _receive_window_state(widget, event):
            # ELL: why is it commented out?
            #new_value = bool(event.new_window_state & Gdk.WindowState.MAXIMIZED)
            #cfg.maximized = new_value
            pass

        window.connect('window-state-event', _receive_window_state)

        # After the window has been set up, we enable events again
        def _enable_window_events():
            self.__ignore_window_events = False
        util.idle_add(_enable_window_events)

        if show_window:
            window.show()
        if cfg.maximized:
            window.maximize()

