import DataProvider

class FileSource(DataProvider.DataProvider):
    def __init__(self):
        DataProvider.DataProvider.__init__(self)
        self.word = "John"
