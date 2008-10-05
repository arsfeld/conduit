import conduit.datatypes.DataType as DataType

class Text(DataType.DataType):
    """
    Wrapper around a text string. Use this as a datatype instead of the
    plain string object
    """
    _name_ = "text"
    def __init__(self, text, **kwargs):
        DataType.DataType.__init__(self)
        self.text = text

    def get_string(self):
        return self.text    

    def __str__(self):
        #only show first 20 characters
        if len(self.text) > 20:
            return self.text[0:19]
        else:
            return self.text
            
    def __getstate__(self):
        data = DataType.DataType.__getstate__(self)
        data['text'] = self.text
        return data

    def __setstate__(self, data):
        self.text = data['text']
        DataType.DataType.__setstate__(self, data)
            
    def get_hash(self):
        return str(hash(self.text))

