from gettext import gettext as _
import DataProviderCategory

#Default Categories for the DataProviders
CATEGORY_FILES = DataProviderCategory.DataProviderCategory(_("Files and Folders"), "computer")
CATEGORY_NOTES = DataProviderCategory.DataProviderCategory(_("Notes"), "tomboy")
CATEGORY_PHOTOS = DataProviderCategory.DataProviderCategory(_("Photos"), "image-x-generic")
CATEGORY_OFFICE = DataProviderCategory.DataProviderCategory(_("Office"), "applications-office")
CATEGORY_SETTINGS = DataProviderCategory.DataProviderCategory(_("Settings"), "applications-system")
CATEGORY_MISC = DataProviderCategory.DataProviderCategory(_("Miscellaneous"), "applications-accessories")
CATEGORY_MEDIA = DataProviderCategory.DataProviderCategory(_("Media"), "applications-multimedia")
CATEGORY_BOOKMARKS = DataProviderCategory.DataProviderCategory(_("Bookmarks"), "user-bookmarks")
CATEGORY_TEST = DataProviderCategory.DataProviderCategory(_("Test"))
