#coding=utf-8

beepEnable = False

if beepEnable:
	import RPi.GPIO as GPIO
	import time
	from threading import Thread
	beepPin = 17

'''
VKeyboard
=========

.. image:: images/vkeyboard.jpg
	:align: right

.. versionadded:: 1.0.8


VKeyboard is an onscreen keyboard for Kivy. Its operation is intended to be
transparent to the user. Using the widget directly is NOT recommended. Read the
section `Request keyboard`_ first.

Modes
-----

This virtual keyboard has a docked and free mode:

* docked mode (:attr:`VKeyboard.docked` = True)
  Generally used when only one person is using the computer, like a tablet or
  personal computer etc.
* free mode: (:attr:`VKeyboard.docked` = False)
  Mostly for multitouch surfaces. This mode allows multiple virtual
  keyboards to be used on the screen.

If the docked mode changes, you need to manually call
:meth:`VKeyboard.setup_mode` otherwise the change will have no impact.
During that call, the VKeyboard, implemented on top of a
:class:`~kivy.uix.scatter.Scatter`, will change the
behavior of the scatter and position the keyboard near the target (if target
and docked mode is set).


Layouts
-------

The virtual keyboard is able to load a custom layout. If you create a new
layout and put the JSON in :file:`<kivy_data_dir>/keyboards/<layoutid>.json`,
you can load it by setting :attr:`VKeyboard.layout` to your layoutid.

The JSON must be structured like this::

	{
		"title": "Title of your layout",
		"description": "Description of your layout",
		"cols": 15,
		"rows": 5,

		...
	}

Then, you need to describe the keys in each row, for either a "normal",
"shift" or a "special" (added in version 1.9.0) mode. Keys for this row
data must be named `normal_<row>`, `shift_<row>` and `special_<row>`.
Replace `row` with the row number.
Inside each row, you will describe the key. A key is a 4 element list in
the format::

	[ <text displayed on the keyboard>, <text to put when the key is pressed>,
	  <text that represents the keycode>, <size of cols> ]

Here are example keys::

	# f key
	["f", "f", "f", 1]
	# capslock
	["\u21B9", "\t", "tab", 1.5]

Finally, complete the JSON::

	{
		...
		"normal_1": [
			["`", "`", "`", 1],    ["1", "1", "1", 1],    ["2", "2", "2", 1],
			["3", "3", "3", 1],    ["4", "4", "4", 1],    ["5", "5", "5", 1],
			["6", "6", "6", 1],    ["7", "7", "7", 1],    ["8", "8", "8", 1],
			["9", "9", "9", 1],    ["0", "0", "0", 1],    ["+", "+", "+", 1],
			["=", "=", "=", 1],    ["\u232b", null, "backspace", 2]
		],

		"shift_1": [ ... ],
		"normal_2": [ ... ],
		"special_2": [ ... ],
		...
	}


Request Keyboard
----------------

The instantiation of the virtual keyboard is controlled by the configuration.
Check `keyboard_mode` and `keyboard_layout` in the :doc:`api-kivy.config`.

If you intend to create a widget that requires a keyboard, do not use the
virtual keyboard directly, but prefer to use the best method available on
the platform. Check the :meth:`~kivy.core.window.WindowBase.request_keyboard`
method in the :doc:`api-kivy.core.window`.

If you want a specific layout when you request the keyboard, you should write
something like this (from 1.8.0, numeric.json can be in the same directory as
your main.py)::

	keyboard = Window.request_keyboard(
		self._keyboard_close, self)
	if keyboard.widget:
		vkeyboard = self._keyboard.widget
		vkeyboard.layout = 'numeric.json'

'''

__all__ = ('VKeyboard', )

from kivy import kivy_data_dir
from kivy.core.window import Window
from kivy.vector import Vector
from kivy.config import Config
from kivy.uix.scatter import Scatter
from kivy.uix.label import Label
from kivy.properties import ObjectProperty, NumericProperty, StringProperty, \
	BooleanProperty, DictProperty, OptionProperty, ListProperty
from kivy.logger import Logger
from kivy.graphics import Color, BorderImage, Canvas
from kivy.core.image import Image
from kivy.resources import resource_find
from kivy.clock import Clock

from io import open
from os.path import join, splitext, basename
from os import listdir
from json import loads

import mmap
import os
import binascii

default_layout_path = join(kivy_data_dir, 'keyboards')
# (簡易五代)","朱邦復發明的簡易倉頡輸入法第五代;Simple Cang Jie 5"
simplex5_table = join(kivy_data_dir, 'table/simplex5.cin')
# (倉頡五代)","朱邦復發明的倉頡輸入法第五代;Cang Jie 5"
cj5_table = join(kivy_data_dir, 'table/cj5.cin')

default_font = join(kivy_data_dir, 'fonts/DejaVuSans.ttf')
default_chinese_font = join(kivy_data_dir, 'fonts/DFSongSd.ttf')

class VKeyboard(Scatter):
	'''
	VKeyboard is an onscreen keyboard with multitouch support.
	Its layout is entirely customizable and you can switch between available
	layouts using a button in the bottom right of the widget.

	:Events:
		`on_key_down`: keycode, internal, modifiers
			Fired when the keyboard received a key down event (key press).
		`on_key_up`: keycode, internal, modifiers
			Fired when the keyboard received a key up event (key release).
	'''

	target = ObjectProperty(None, allownone=True)
	'''Target widget associated with the VKeyboard. If set, it will be used to
	send keyboard events. If the VKeyboard mode is "free", it will also be used
	to set the initial position.

	:attr:`target` is an :class:`~kivy.properties.ObjectProperty` instance and
	defaults to None.
	'''

	callback = ObjectProperty(None, allownone=True)
	'''Callback can be set to a function that will be called if the
	VKeyboard is closed by the user.

	:attr:`target` is an :class:`~kivy.properties.ObjectProperty` instance and
	defaults to None.
	'''

	layout = StringProperty(None)
	'''Layout to use for the VKeyboard. By default, it will be the
	layout set in the configuration, according to the `keyboard_layout`
	in `[kivy]` section.

	.. versionchanged:: 1.8.0
		If layout is a .json filename, it will loaded and added to the
		available_layouts.

	:attr:`layout` is a :class:`~kivy.properties.StringProperty` and defaults
	to None.
	'''

	layout_path = StringProperty(default_layout_path)
	'''Path from which layouts are read.

	:attr:`layout` is a :class:`~kivy.properties.StringProperty` and
	defaults to :file:`<kivy_data_dir>/keyboards/`
	'''

	available_layouts = DictProperty({})
	'''Dictionary of all available layouts. Keys are the layout ID, and the
	value is the JSON (translated into a Python object).

	:attr:`available_layouts` is a :class:`~kivy.properties.DictProperty` and
	defaults to {}.
	'''

	docked = BooleanProperty(False)
	'''Indicate whether the VKeyboard is docked on the screen or not. If you
	change it, you must manually call :meth:`setup_mode` otherwise it will have
	no impact. If the VKeyboard is created by the Window, the docked mode will
	be automatically set by the configuration, using the `keyboard_mode` token
	in `[kivy]` section.

	:attr:`docked` is a :class:`~kivy.properties.BooleanProperty` and defaults
	to False.
	'''

	margin_hint = ListProperty([.05, .06, .05, .06])
	'''Margin hint, used as spacing between keyboard background and keys
	content. The margin is composed of four values, between 0 and 1::

		margin_hint = [top, right, bottom, left]

	The margin hints will be multiplied by width and height, according to their
	position.

	:attr:`margin_hint` is a :class:`~kivy.properties.ListProperty` and
	defaults to [.05, .06, .05, .06]
	'''

	key_margin = ListProperty([2, 2, 2, 2])
	'''Key margin, used to create space between keys. The margin is composed of
	four values, in pixels::

		key_margin = [top, right, bottom, left]

	:attr:`key_margin` is a :class:`~kivy.properties.ListProperty` and defaults
	to [2, 2, 2, 2]
	'''

	font_size = NumericProperty(20.)
	'''font_size, specifies the size of the text on the virtual keyboard keys.
	It should be kept within limits to ensure the text does not extend beyond
	the bounds of the key or become too small to read.

	.. versionadded:: 1.10.0

	:attr:`font_size` is a :class:`~kivy.properties.NumericProperty` and
	defaults to 20.
	'''

	background_color = ListProperty([1, 1, 1, 1])
	'''Background color, in the format (r, g, b, a). If a background is
	set, the color will be combined with the background texture.

	:attr:`background_color` is a :class:`~kivy.properties.ListProperty` and
	defaults to [1, 1, 1, 1].
	'''

	background = StringProperty(
		'atlas://data/images/defaulttheme/vkeyboard_background')
	'''Filename of the background image.

	:attr:`background` is a :class:`~kivy.properties.StringProperty` and
	defaults to :file:`atlas://data/images/defaulttheme/vkeyboard_background`.
	'''

	background_disabled = StringProperty(
		'atlas://data/images/defaulttheme/vkeyboard_disabled_background')
	'''Filename of the background image when the vkeyboard is disabled.

	.. versionadded:: 1.8.0

	:attr:`background_disabled` is a
	:class:`~kivy.properties.StringProperty` and defaults to
	:file:`atlas://data/images/defaulttheme/vkeyboard__disabled_background`.

	'''

	key_background_color = ListProperty([1, 1, 1, 1])
	'''Key background color, in the format (r, g, b, a). If a key background is
	set, the color will be combined with the key background texture.

	:attr:`key_background_color` is a :class:`~kivy.properties.ListProperty`
	and defaults to [1, 1, 1, 1].
	'''

	key_background_normal = StringProperty(
		'atlas://data/images/defaulttheme/vkeyboard_key_normal')
	'''Filename of the key background image for use when no touches are active
	on the widget.

	:attr:`key_background_normal` is a :class:`~kivy.properties.StringProperty`
	and defaults to
	:file:`atlas://data/images/defaulttheme/vkeyboard_key_normal`.
	'''

	key_disabled_background_normal = StringProperty(
		'atlas://data/images/defaulttheme/vkeyboard_key_normal')
	'''Filename of the key background image for use when no touches are active
	on the widget and vkeyboard is disabled.

	.. versionadded:: 1.8.0

	:attr:`key_disabled_background_normal` is a
	:class:`~kivy.properties.StringProperty` and defaults to
	:file:`atlas://data/images/defaulttheme/vkeyboard_disabled_key_normal`.

	'''

	key_background_down = StringProperty(
		'atlas://data/images/defaulttheme/vkeyboard_key_down')
	'''Filename of the key background image for use when a touch is active
	on the widget.

	:attr:`key_background_down` is a :class:`~kivy.properties.StringProperty`
	and defaults to
	:file:`atlas://data/images/defaulttheme/vkeyboard_key_down`.
	'''

	background_border = ListProperty([16, 16, 16, 16])
	'''Background image border. Used for controlling the
	:attr:`~kivy.graphics.vertex_instructions.BorderImage.border` property of
	the background.

	:attr:`background_border` is a :class:`~kivy.properties.ListProperty` and
	defaults to [16, 16, 16, 16]
	'''

	key_border = ListProperty([8, 8, 8, 8])
	'''Key image border. Used for controlling the
	:attr:`~kivy.graphics.vertex_instructions.BorderImage.border` property of
	the key.

	:attr:`key_border` is a :class:`~kivy.properties.ListProperty` and
	defaults to [16, 16, 16, 16]
	'''

	# XXX internal variables
	layout_mode = OptionProperty('normal',
		options=('normal', 'shift', 'special', 'chinese'))
	layout_geometry = DictProperty({})
	have_capslock = BooleanProperty(False)
	have_shift = BooleanProperty(False)
	have_special = BooleanProperty(False)
	have_chinese = BooleanProperty(False)
	active_keys = DictProperty({})
	lines = ListProperty()
	chinese_keys = StringProperty()
	chinese_internal = StringProperty()
	select_chinese = StringProperty()
	select_chinese_pos = 0
	chinese_input = 0
	font_name = StringProperty(default_font)
	chinese_font_name = StringProperty(default_chinese_font)
	repeat_touch = ObjectProperty(allownone=True)

	_start_repeat_key_ev = None
	_repeat_key_ev = None

	__events__ = ('on_key_down', 'on_key_up', 'on_textinput')

	def __init__(self, **kwargs):
		if beepEnable:
			# Set up GPIO:
			GPIO.setmode(GPIO.BCM)
			GPIO.setwarnings(False)
			GPIO.setup(beepPin, GPIO.OUT)
			GPIO.output(beepPin, GPIO.LOW)

		# XXX move to style.kv
		if 'size_hint' not in kwargs:
			if 'size_hint_x' not in kwargs:
				self.size_hint_x = None
			if 'size_hint_y' not in kwargs:
				self.size_hint_y = None
		if 'size' not in kwargs:
			if 'width' not in kwargs:
				self.width = 700
			if 'height' not in kwargs:
				self.height = 200
		if 'scale_min' not in kwargs:
			self.scale_min = .4
		if 'scale_max' not in kwargs:
			self.scale_max = 1.6
		if 'docked' not in kwargs:
			self.docked = False

		layout_mode = self._trigger_update_layout_mode = Clock.create_trigger(
			self._update_layout_mode)
		layouts = self._trigger_load_layouts = Clock.create_trigger(
			self._load_layouts)
		layout = self._trigger_load_layout = Clock.create_trigger(
			self._load_layout)
		fbind = self.fbind

		fbind('docked', self.setup_mode)
		fbind('have_shift', layout_mode)
		fbind('have_capslock', layout_mode)
		fbind('have_special', layout_mode)
		fbind('layout_path', layouts)
		fbind('layout', layout)
		super(VKeyboard, self).__init__(**kwargs)

		# load all the layouts found in the layout_path directory
		self._load_layouts()

		# ensure we have default layouts
		available_layouts = self.available_layouts
		if not available_layouts:
			Logger.critical('VKeyboard: unable to load default layouts')

		# load the default layout from configuration
		if self.layout is None:
			self.layout = Config.get('kivy', 'keyboard_layout')
		else:
			# ensure the current layout is found on the available layout
			self._trigger_load_layout()

		# update layout mode (shift or normal)
		self._trigger_update_layout_mode()

		# create a top layer to draw active keys on
		with self.canvas:
			self.background_key_layer = Canvas()
			self.active_keys_layer = Canvas()
		self.readChineseTable()

	def on_disabled(self, intance, value):
		self.refresh_keys()

	def _update_layout_mode(self, *l):
		# update mode according to capslock and shift key
		mode = self.have_capslock != self.have_shift
		mode = 'shift' if mode else 'normal'
		if self.have_special:
			mode = "special"
		if mode != self.layout_mode:
			self.layout_mode = mode
			self.refresh(False)

	def _load_layout(self, *largs):
		# ensure new layouts are loaded first
		if self._trigger_load_layouts.is_triggered:
			self._load_layouts()
			self._trigger_load_layouts.cancel()

		value = self.layout
		available_layouts = self.available_layouts

		# it's a filename, try to load it directly
		if self.layout[-5:] == '.json':
			if value not in available_layouts:
				fn = resource_find(self.layout)
				self._load_layout_fn(fn, self.layout)

		if not available_layouts:
			return
		if value not in available_layouts and value != 'qwerty':
			Logger.error(
				'Vkeyboard: <%s> keyboard layout mentioned in '
				'conf file was not found, fallback on qwerty' %
				value)
			self.layout = 'qwerty'
		self.refresh(True)

	def _load_layouts(self, *largs):
		# first load available layouts from json files
		# XXX fix to be able to reload layout when path is changing
		value = self.layout_path
		for fn in listdir(value):
			self._load_layout_fn(join(value, fn),
								 basename(splitext(fn)[0]))

	def _load_layout_fn(self, fn, name):
		available_layouts = self.available_layouts
		if fn[-5:] != '.json':
			return
		with open(fn, 'r', encoding='utf-8') as fd:
			json_content = fd.read()
			layout = loads(json_content)
		available_layouts[name] = layout

	def setup_mode(self, *largs):
		'''Call this method when you want to readjust the keyboard according to
		options: :attr:`docked` or not, with attached :attr:`target` or not:

		* If :attr:`docked` is True, it will call :meth:`setup_mode_dock`
		* If :attr:`docked` is False, it will call :meth:`setup_mode_free`

		Feel free to overload these methods to create new
		positioning behavior.
		'''
		if self.docked:
			self.setup_mode_dock()
		else:
			self.setup_mode_free()

	def setup_mode_dock(self, *largs):
		'''Setup the keyboard in docked mode.

		Dock mode will reset the rotation, disable translation, rotation and
		scale. Scale and position will be automatically adjusted to attach the
		keyboard to the bottom of the screen.

		.. note::
			Don't call this method directly, use :meth:`setup_mode` instead.
		'''
		self.do_translation = False
		self.do_rotation = False
		self.do_scale = False
		self.rotation = 0
		win = self.get_parent_window()
		scale = win.width / float(self.width)
		self.scale = scale
		self.pos = 0, 0
		win.bind(on_resize=self._update_dock_mode)

	def _update_dock_mode(self, win, *largs):
		scale = win.width / float(self.width)
		self.scale = scale
		self.pos = 0, 0

	def setup_mode_free(self):
		'''Setup the keyboard in free mode.

		Free mode is designed to let the user control the position and
		orientation of the keyboard. The only real usage is for a multiuser
		environment, but you might found other ways to use it.
		If a :attr:`target` is set, it will place the vkeyboard under the
		target.

		.. note::
			Don't call this method directly, use :meth:`setup_mode` instead.
		'''
		self.do_translation = True
		self.do_rotation = True
		self.do_scale = True
		target = self.target
		if not target:
			return

		# NOTE all math will be done in window point of view
		# determine rotation of the target
		a = Vector(1, 0)
		b = Vector(target.to_window(0, 0))
		c = Vector(target.to_window(1, 0)) - b
		self.rotation = -a.angle(c)

		# determine the position of center/top of the keyboard
		dpos = Vector(self.to_window(self.width / 2., self.height))

		# determine the position of center/bottom of the target
		cpos = Vector(target.to_window(target.center_x, target.y))

		# the goal now is to map both point, calculate the diff between them
		diff = dpos - cpos

		# we still have an issue, self.pos represent the bounding box,
		# not the 0,0 coordinate of the scatter. we need to apply also
		# the diff between them (inside and outside coordinate matrix).
		# It's hard to explain, but do a scheme on a paper, write all
		# the vector i'm calculating, and you'll understand. :)
		diff2 = Vector(self.x + self.width / 2., self.y + self.height) - \
			Vector(self.to_parent(self.width / 2., self.height))
		diff -= diff2

		# now we have a good "diff", set it as a pos.
		self.pos = -diff

	def change_layout(self):
		# XXX implement popup with all available layouts
		pass

	def refresh(self, force=False):
		'''(internal) Recreate the entire widget and graphics according to the
		selected layout.
		'''
		self.clear_widgets()
		if force:
			self.refresh_keys_hint()
		self.refresh_keys()
		self.refresh_active_keys_layer()

	def refresh_active_keys_layer(self):
		self.active_keys_layer.clear()

		active_keys = self.active_keys
		layout_geometry = self.layout_geometry
		background = resource_find(self.key_background_down)
		texture = Image(background, mipmap=True).texture

		with self.active_keys_layer:
			Color(1, 1, 1)
			for line_nb, index in active_keys.values():
				pos, size = layout_geometry['LINE_%d' % line_nb][index]
				BorderImage(texture=texture, pos=pos, size=size,
							border=self.key_border)

	def refresh_keys_hint(self):
		layout = self.available_layouts[self.layout]
		layout_cols = layout['cols']
		layout_rows = layout['rows']
		layout_geometry = self.layout_geometry
		mtop, mright, mbottom, mleft = self.margin_hint

		# get relative EFFICIENT surface of the layout without external margins
		el_hint = 1. - mleft - mright
		eh_hint = 1. - mtop - mbottom
		ex_hint = 0 + mleft
		ey_hint = 0 + mbottom

		# get relative unit surface
		uw_hint = (1. / layout_cols) * el_hint
		uh_hint = (1. / layout_rows) * eh_hint
		layout_geometry['U_HINT'] = (uw_hint, uh_hint)

		# calculate individual key RELATIVE surface and pos (without key
		# margin)
		current_y_hint = ey_hint + eh_hint
		for line_nb in range(1, layout_rows + 1):
			current_y_hint -= uh_hint
			# get line_name
			line_name = '%s_%d' % (self.layout_mode, line_nb)
			line_hint = 'LINE_HINT_%d' % line_nb
			layout_geometry[line_hint] = []
			current_x_hint = ex_hint
			# go through the list of keys (tuples of 4)
			for key in layout[line_name]:
				# calculate relative pos, size
				layout_geometry[line_hint].append([
					(current_x_hint, current_y_hint),
					(key[3] * uw_hint, uh_hint)])
				current_x_hint += key[3] * uw_hint

		self.layout_geometry = layout_geometry

	def refresh_keys(self):
		layout = self.available_layouts[self.layout]
		layout_rows = layout['rows']
		layout_geometry = self.layout_geometry
		w, h = self.size
		kmtop, kmright, kmbottom, kmleft = self.key_margin
		uw_hint, uh_hint = layout_geometry['U_HINT']

		for line_nb in range(1, layout_rows + 1):
			llg = layout_geometry['LINE_%d' % line_nb] = []
			llg_append = llg.append
			for key in layout_geometry['LINE_HINT_%d' % line_nb]:
				x_hint, y_hint = key[0]
				w_hint, h_hint = key[1]
				kx = x_hint * w
				ky = y_hint * h
				kw = w_hint * w
				kh = h_hint * h

				# now adjust, considering the key margin
				kx = int(kx + kmleft)
				ky = int(ky + kmbottom)
				kw = int(kw - kmleft - kmright)
				kh = int(kh - kmbottom - kmtop)

				pos = (kx, ky)
				size = (kw, kh)
				llg_append((pos, size))

		self.layout_geometry = layout_geometry
		self.draw_keys()

	def draw_keys(self):
		layout = self.available_layouts[self.layout]
		layout_rows = layout['rows']
		layout_geometry = self.layout_geometry
		layout_mode = self.layout_mode

		# draw background
		background = resource_find(self.background_disabled
								   if self.disabled else
								   self.background)
		texture = Image(background, mipmap=True).texture
		self.background_key_layer.clear()
		with self.background_key_layer:
			Color(*self.background_color)
			BorderImage(texture=texture, size=self.size,
						border=self.background_border)

		# XXX separate drawing the keys and the fonts to avoid
		# XXX reloading the texture each time

		# first draw keys without the font
		key_normal = resource_find(self.key_background_disabled_normal
								   if self.disabled else
								   self.key_background_normal)
		texture = Image(key_normal, mipmap=True).texture
		with self.background_key_layer:
			for line_nb in range(1, layout_rows + 1):
				for pos, size in layout_geometry['LINE_%d' % line_nb]:
						BorderImage(texture=texture, pos=pos, size=size,
									border=self.key_border)

		# then draw the text
		for line_nb in range(1, layout_rows + 1):
			key_nb = 0
			for pos, size in layout_geometry['LINE_%d' % line_nb]:
				# retrieve the relative text
				fontName = self.chinese_font_name
				if line_nb == 5 and key_nb == 10:
					if self.chinese_input == 0:
						text = u'簡易'
					elif self.chinese_input == 1:
						text = u'倉頡'
				elif line_nb == 5 and key_nb == 9:
					text = layout[layout_mode + '_' + str(line_nb)][key_nb][0]
				else:
					text = layout[layout_mode + '_' + str(line_nb)][key_nb][0]
					if not self.have_chinese:
						fontName = self.font_name
					elif not text.isalpha():
						fontName = self.font_name
				z = Label(text=text, font_size=self.font_size, pos=pos, size=size, font_name=fontName)
				#z = Label(text=text, font_size=self.font_size, pos=pos, size=size, font_name=self.font_name)
				self.add_widget(z)
				key_nb += 1

	def on_key_down(self, *largs):
		pass

	def on_key_up(self, *largs):
		pass

	def on_textinput(self, *largs):
		pass

	def get_key_at_pos(self, x, y):
		w, h = self.size
		x_hint = x / w
		# focus on the surface without margins
		layout_geometry = self.layout_geometry
		layout = self.available_layouts[self.layout]
		layout_rows = layout['rows']
		mtop, mright, mbottom, mleft = self.margin_hint

		# get the line of the layout
		e_height = h - (mbottom + mtop) * h  # efficient height in pixels
		line_height = e_height / layout_rows  # line height in px
		y = y - mbottom * h
		line_nb = layout_rows - int(y / line_height)

		if line_nb > layout_rows:
			line_nb = layout_rows
		if line_nb < 1:
			line_nb = 1

		# get the key within the line
		key_index = ''
		current_key_index = 0
		for key in layout_geometry['LINE_HINT_%d' % line_nb]:
			if x_hint >= key[0][0] and x_hint < key[0][0] + key[1][0]:
				key_index = current_key_index
				break
			else:
				current_key_index += 1
		if key_index == '':
			return None

		# get the full character
		key = layout['%s_%d' % (self.layout_mode, line_nb)][key_index]

		return [key, (line_nb, key_index)]

	def collide_margin(self, x, y):
		'''Do a collision test, and return True if the (x, y) is inside the
		vkeyboard margin.
		'''
		mtop, mright, mbottom, mleft = self.margin_hint
		x_hint = x / self.width
		y_hint = y / self.height
		if x_hint > mleft and x_hint < 1. - mright \
				and y_hint > mbottom and y_hint < 1. - mtop:
			return False
		return True

	def clear_chinese(self):
		self.select_chinese = ''
		self.chinese_internal = ''
		self.select_chinese_pos = 0
		self.chinese_keys = ''

	def readChineseTable(self):
		if self.chinese_input == 0:
			fo = open(simplex5_table, encoding='utf-8')
			self.lines = fo.readlines()
			fo.close()
		else:
			fo = open(cj5_table, encoding='utf-8')
			self.lines = fo.readlines()
			fo.close()

	def process_key_on(self, touch):
		result = False

		if not touch:
			return
		x, y = self.to_local(*touch.pos)
		key = self.get_key_at_pos(x, y)
		if not key:
			return

		if beepEnable:
			Thread(target=self.beep()).start()

		key_data = key[0]
		displayed_char, internal, special_char, size = key_data
		line_nb, key_index = key[1]

		# save pressed key on the touch
		ud = touch.ud[self.uid] = {}
		ud['key'] = key

		# for caps lock or shift only:
		uid = touch.uid
		if special_char is not None:
			# Do not repeat special keys
			if special_char in ('capslock', 'shift', 'layout', 'special', 'chinese'):
				if self._start_repeat_key_ev is not None:
					self._start_repeat_key_ev.cancel()
					self._start_repeat_key_ev = None
				self.repeat_touch = None
			if special_char == 'capslock':
				self.have_capslock = not self.have_capslock
				self.have_chinese = False
				uid = -1
			elif special_char == 'shift':
				self.have_shift = True
				self.have_chinese = False
			elif special_char == 'special':
				self.have_special = True
			elif special_char == 'layout':
				self.change_layout()
			elif special_char == 'chinese':
				self.clear_chinese()
				if self.have_chinese:
					self.have_chinese = False
					self.layout_mode = 'normal'
				elif self.layout_mode == 'normal':
					self.have_chinese = True
					self.layout_mode = 'chinese'
					result = False
				self.refresh(False)
			elif special_char == 'input':
				self.chinese_input = self.chinese_input + 1
				if self.chinese_input > 1:
					self.chinese_input = 0
				self.readChineseTable()
				self.clear_chinese()
				self.refresh()

		# save key as an active key for drawing
		redraw = True
		if self.have_chinese and not special_char in ('capslock', 'shift', 'layout', 'special', 'enter', 'tab'):
			if special_char == 'escape':
				Window.release_all_keyboards()
			else:
				if special_char == 'backspace':
					i = len(self.chinese_internal)
					if i > 0:
						self.chinese_internal = self.chinese_internal[:i-1]
						self.chinese_keys = self.chinese_keys[:i-1]
						self.find_chinese_internal(self.chinese_keys)
					else:
						result = True
				elif not special_char in ('chinese', 'input'):
					if line_nb == 5:
						if special_char > '0' and special_char < '7' and self.chinese_keys != '':
							i = self.select_chinese_pos + (ord(special_char) - 0x31)
							if len(self.select_chinese) > i:
								chinese = self.select_chinese[i]
								if len(chinese)>0:
									result = True
									internal = chinese
									self.clear_chinese()
						elif special_char == 'spacebar':
							self.clear_chinese()
						elif len(self.select_chinese) > 0:
							if special_char == 'N':
								if len(self.select_chinese) > (self.select_chinese_pos + 6):
									self.select_chinese_pos = self.select_chinese_pos + 6
								else:
									redraw = False
							elif special_char == 'P':
								if self.select_chinese_pos > 5:
									self.select_chinese_pos = self.select_chinese_pos - 6
								else:
									redraw = False
					elif special_char.isalpha():   # check special_char within [a..z]
						# 簡易五代
						if self.chinese_input == 0:
							if len(self.chinese_keys)<2:
								self.chinese_keys = self.chinese_keys + special_char
								self.chinese_internal = self.chinese_internal + internal
							else:
								self.chinese_keys = special_char
								self.chinese_internal = internal
						# 倉頡五代
						elif self.chinese_input == 1:
							if len(self.chinese_keys)<5:
								self.chinese_keys = self.chinese_keys + special_char
								self.chinese_internal = self.chinese_internal + internal
							else:
								self.chinese_keys = special_char
								self.chinese_internal = internal
						self.find_chinese_internal(self.chinese_keys)
					else:
						result = True
				if redraw:
					self.draw_chinese_keys()
		else:
			result = True
		if result:
			# send info to the bus
			b_keycode = special_char
			b_modifiers = self._get_modifiers()
			if self.get_parent_window().__class__.__module__ == \
				'kivy.core.window.window_sdl2' and internal:
				self.dispatch('on_textinput', internal)
			else:
				self.dispatch('on_key_down', b_keycode, internal, b_modifiers)
		self.active_keys[uid] = key[1]
		self.refresh_active_keys_layer()

	def find_chinese_internal(self, ch):
		self.refresh()
		self.select_chinese = ''
		self.select_chinese_pos = 0
		if len(self.chinese_keys) == 0:
			return

		ok = False
		for line in self.lines:
			i = line.find(ch + ' ')
			if i == 0:
				ok = True
				# remove '\n'
				line = line[:len(line)-1]
				s = line[len(ch)+1:]
				self.select_chinese = self.select_chinese + s
			elif ok:
				return

	def draw_chinese_keys(self):
		layout_geometry = self.layout_geometry

		self.refresh(False)
		# then draw the text
		key_nb = 0
		chinese_pos = self.select_chinese_pos
		for pos, size in layout_geometry['LINE_5']:
			# retrieve the relative text
			text = ' '
			fontName = self.chinese_font_name
			if key_nb == 0:
				fontName = self.font_name
				if chinese_pos != 0:
					text = u"\u25c0"
				else:
					text = u"\u25c1"
			elif key_nb == 7:
				fontName = self.font_name
				if len(self.select_chinese) > (self.select_chinese_pos + 8):
					text = u"\u25b6"
				else:
					text = u"\u25b7"
			elif key_nb > 0 and key_nb < 7 and len(self.select_chinese) > chinese_pos:
				text = self.select_chinese[chinese_pos]
				chinese_pos = chinese_pos + 1
			elif key_nb == 8:
				text = self.chinese_internal
			z = Label(text=text, font_size=self.font_size, pos=pos, size=size, font_name=fontName)
			self.add_widget(z)
			key_nb += 1

	def process_key_up(self, touch):
		uid = touch.uid
		if self.uid not in touch.ud:
			return

		# save pressed key on the touch
		key_data, key = touch.ud[self.uid]['key']
		displayed_char, internal, special_char, size = key_data

		# send info to the bus
		b_keycode = special_char
		b_modifiers = self._get_modifiers()
		self.dispatch('on_key_up', b_keycode, internal, b_modifiers)

		if special_char == 'capslock':
			uid = -1

		if uid in self.active_keys:
			self.active_keys.pop(uid, None)
			if special_char == 'shift':
				self.have_shift = False
			elif special_char == 'special':
				self.have_special = False
			if special_char == 'capslock' and self.have_capslock:
				self.active_keys[-1] = key
			self.refresh_active_keys_layer()

	def _get_modifiers(self):
		ret = []
		if self.have_shift:
			ret.append('shift')
		if self.have_capslock:
			ret.append('capslock')
		if self.have_chinese:
			ret.append('chinese')
		return ret

	def _start_repeat_key(self, *kwargs):
		self._repeat_key_ev = Clock.schedule_interval(self._repeat_key, 0.05)

	def _repeat_key(self, *kwargs):
		self.process_key_on(self.repeat_touch)

	def on_touch_down(self, touch):
		x, y = touch.pos
		if not self.collide_point(x, y):
			return
		if self.disabled:
			return True

		x, y = self.to_local(x, y)
		if not self.collide_margin(x, y):
			if self.repeat_touch is None:
				self._start_repeat_key_ev = Clock.schedule_once(
					self._start_repeat_key, 0.5)
			self.repeat_touch = touch

			self.process_key_on(touch)
			touch.grab(self, exclusive=True)

		else:
			super(VKeyboard, self).on_touch_down(touch)
		return True

	def on_touch_up(self, touch):
		if touch.grab_current is self:
			self.process_key_up(touch)

			if self._start_repeat_key_ev is not None:
				self._start_repeat_key_ev.cancel()
				self._start_repeat_key_ev = None
			if touch == self.repeat_touch:
				if self._repeat_key_ev is not None:
					self._repeat_key_ev.cancel()
					self._repeat_key_ev = None
				self.repeat_touch = None

		return super(VKeyboard, self).on_touch_up(touch)

	#--------------------------------------------------------
	def beep(self):
		if beepEnable:
			GPIO.output(beepPin, GPIO.HIGH)
			time.sleep(0.1)
			# turn off the beeper:
			GPIO.output(beepPin, GPIO.LOW)


if __name__ == '__main__':
	from kivy.base import runTouchApp
	vk = VKeyboard(layout='chinese')
	runTouchApp(vk)
