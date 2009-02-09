
Configuration
=============

Architecture
------------

The basic architecture is divided between three classes and their implementatins: a Configurator, a Container, and an Item.

:class:`Configurator`
  Contains one or more Containers. It is basically a widget that display the containers and has some action buttons, like OK, Cancel and Apply, and pass those commands to each child Container. There are two implementations of this class, one is the EmbedConfigurator and the other is a WindowConfigurator. 

  :class:`conduit.gtkui.EmbedConfigurator`
    Used to be embed inside other windows, like a sidepane. It supports multiple Containers by stacking them vertically, and contains an Apply and Cancel button at the bottom.
  :class:`conduit.gtkui.WindowConfigurator.WindowConfigurator`
    Shows a separate modal window. Has an OK and Cancel button at the bottom, and clicking in any of them closes the window.

  A dataprovider usually dont have to care about any of these. The current implementation is using WindowConfigurator to mimic the old behaviour. They were implemented in a way that switching between one and another does not require any code change.

  There is usually only one instance of a Configurator per application, and that instance is reused as needed.

:class:`conduit.gtkui.ConfigContainer.ConfigContainer`
  Contains one or more items. This is the class that Dataproviders will interact with most. An instance is created when needed by a dataprovider in :meth:`conduit.DataProvider.DataProvider.get_config_container` and that instance is passed to :meth:`conduit.DataProvider.DataProvider.config_setup` so that subclasses can define their own configuration items.

  Items can be added with :meth:`conduit.gtkui.ConfigContainer.ConfigContainer.add_item`, which are enclosed in sections, added with :meth:`conduit.gtkui.ConfigContainer.ConfigContainer.add_section`, as better explained below.

  A Container instance is usually created only the first time it is needed, and it is used again when :meth:`conduit.DataProvider.DataProvider.get_config_container` is called.

  The basic Container interface provided by :class:`conduit.Configurator.BaseConfigContainer`, and inherited by :class:`conduit.gtkui.ConfigContainer.ConfigContainer`, is very simple and does not include items or sections. This way any dataprovider can provide their own implementation of a Container, if the current Container API does not suit it's needs. This is used in the Files dataprovider, to provide an experience not availiable with items.

:class:`conduit.gtkui.ConfigWidgets.ConfigItem`
  A simple wrapper for widgets. It exposes a value that is directly translated to the contents of the widget. 

  Supporting most basic types without exposing much implementation details, they provide a good abstraction over the current widget toolkit being used.


Inside a dataprovider
---------------------

This is how it is supposed to be used inside a dataprovider.

There must exist a *config_setup(self, config_container)* function.
Config items are added with *config.add_item(item_name, item_type, \*\*properties)*, and sections with *config.add_section(section_name, \*\*section_properties)*. 

Item types describes the widgets they will use. Currently supported items are: 

* "text"
* "radio"
* "spin"
* "combo"
* "list"
* "check"
* "label"
* "button"

Item properties define their look and behaviour.

This is best described with an example, from the F-Spot dataprovider:

.. sourcecode:: python

    def config_setup(self, config):
        config.add_section("Tags")
        tags_config = config.add_item("Tags", "list",
            config_name = 'tags',
            choices = self._get_all_tags(),
        )
        def add_tag_cb(button):
            text = tag_name_config.get_value()
            tags = text.split(',')
            for tag in tags:
                self._create_tag (tag.strip ())   
            tags_config.set_choices(self._get_all_tags())
            tag_name_config.set_value('')
        add_tags_section = config.add_section("Add tags")
        tag_name_config = config.add_item("Tag name", "text",
            initial_value = ""
        )
        config.add_item("Add tag", "button",
            action = add_tag_cb
        )

Reference
---------

.. autoclass:: conduit.gtkui.ConfigContainer.ConfigContainer
   :members:
   
.. autoclass:: conduit.gtkui.WindowConfigurator.WindowConfigurator
   :members:   
   
Configuration Items
^^^^^^^^^^^^^^^^^^^
   
.. autoclass:: conduit.gtkui.ConfigWidgets.ConfigItem
   :members:


