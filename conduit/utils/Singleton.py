#!/usr/bin/env python
# -*- coding: UTF8 -*-
#
#  GObjectSingleton.py
#  Copyright (c) 2006 INdT (Instituto Nokia de Tecnologia)
#  Author: Eduardo de Barros Lima <eduardo.lima@indt.org.br>
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public License as
#  published by the Free Software Foundation; either version 2.1 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301
#  USA

import gobject

class GObjectSingleton(gobject.GObjectMeta):

    def __init__(cls, name, base, dict):
        gobject.GObjectMeta.__init__(cls, name, base, dict)
        cls.__instance = None
        cls.__copy__ = lambda self: self
        cls.__deepcopy__ = lambda self, memo=None: self

    def __call__(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = super(GObjectSingleton, cls).__call__(*args, **kwargs)
        return cls.__instance

class Singleton:
    """
    A model that implements the Singleton pattern.
    """

    __metaclass__ = GObjectSingleton

    pass

