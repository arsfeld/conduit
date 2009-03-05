from gettext import gettext as _

HINT_BLANK_CANVAS           = -100
HINT_ADD_DATAPROVIDER       = -101
HINT_RIGHT_CLICK_CONFIGURE  = -102

HINT_TEXT = {
    HINT_BLANK_CANVAS:(             _("What Do You Want to Synchronize?"),
                                    _("Drag and Drop a Data Provider on the Canvas"),
                                    True),
    HINT_ADD_DATAPROVIDER:(         _("Synchronization Group Created"),
                                    _("Add Another Data Provider to the Group to Synchronize it"),
                                    False),
    HINT_RIGHT_CLICK_CONFIGURE:(    _("You Are Now Ready to Synchronize"),
                                    _("Right Click on Group for Options"),
                                    False)
}

PRECONFIGIRED_CONDUITS = {
    #source,sinc                            #comment                        
        #twoway
    ("FolderTwoWay","FolderTwoWay"):(       _("Synchronize Two Folders"),      
        True    ),
    ("FolderTwoWay","BoxDotNetTwoWay"):(    _("Backup Folder to Box.net"),       
        False   ),
    ("FSpotDbusTwoWay","FlickrTwoWay"):(    _("Synchronize Tagged F-Spot Photos to Flickr"),       
        False   )
}


