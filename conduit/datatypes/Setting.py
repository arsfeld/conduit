import conduit.datatypes.DataType as DataType

class Setting(DataType.DataType):
    """
    Represents a users 'setting' or a preference. Basically a key:value type
    """
    _name_ = "setting"
    def __init__(self, key, value, **kwargs):
        DataType.DataType.__init__(self)
        self.key = key
        self.value = value

    def __getstate__(self):
        data = DataType.DataType.__getstate__(self)
        data["key"] = self.key
        data["value"] = self.value
        return data

    def __setstate__(self, data):
        self.key = data["key"]
        self.value = data["value"]
        DataType.DataType.__setstate__(self, data)

    def get_hash(self):
        return str(hash( (self.key,self.value) ))
