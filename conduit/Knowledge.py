HINT_BLANK_CANVAS           = -100
HINT_ADD_DATAPROVIDER       = -101
HINT_RIGHT_CLICK_CONFIGURE  = -102

HINT_TEXT = {
    HINT_BLANK_CANVAS:(             "What Do You Want to Synchronize?",
                                    "Drag and Drop a Data Provider on the Canvas",
                                    True),
    HINT_ADD_DATAPROVIDER:(         "Synchronization Group Created",
                                    "Add Another Data Provider to the Group to Synchronize it",
                                    False),
    HINT_RIGHT_CLICK_CONFIGURE:(    "You Are Now Ready to Synchronize",
                                    "Right Click on Group for Options",
                                    False)
}

PRECONFIGIRED_CONDUITS = {
    #source,sinc                            #comment                        
        #twoway
    ("FolderTwoWay","FolderTwoWay"):(       "Synchronize Two Folders",      
        True    ),
    ("FolderTwoWay","BoxDotNetTwoWay"):(    "Backup Folder to Box.net",       
        False   ),
    ("FSpotDbusTwoWay","FlickrTwoWay"):(    "Synchronize Tagged F-Spot Photos to Flickr",       
        False   )
}


