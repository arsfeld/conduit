import conduit.datatypes

class DataType:
    """
    Base DataType which represents any thing 
    which can be synchronized between two DataProviders
    """
    def __init__(self,type_name):
        self.type_name = type_name

    def compare(self, from_type, to_type):
        """
        Synchronize
        """
        return conduit.datatypes.EQUAL

