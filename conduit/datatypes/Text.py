import conduit.datatypes.DataType as DataType

class Text(DataType.DataType):
    """
    Wrapper around a text string. Use this as a datatype instead of the
    plain string object
    """
    _name_ = "text"
    def __init__(self, **kwargs):
        DataType.DataType.__init__(self)
        self.text = kwargs.get("text","")

    def get_string(self):
        return self.text    

    def __str__(self):
        #only show first 20 characters
        if len(self.text) > 20:
            return self.text[0:19]
        else:
            return self.text
            
    def get_hash(self):
        return hash(self.text)

