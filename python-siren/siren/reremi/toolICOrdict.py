import collections
import pdb

class ICOrdict(collections.MutableMapping):
    """
    A dict like object that keeps track of the changes.

    Initialization and use like normal dict, except that doesn't support initialization from keywords
    (as in 'dict(one=1, two=2)'). Has property isChanged, which is initially set to False, unless other
    value is given to __init__() as second argument.
    The following actions set d.isChanged to True for ICDict d:
    d[key] = value
    del d[key]
    d.clear()
    d.pop(key)
    d.popitem()
    d.setdefault(key)
    d.update()

    Method d.copy() will return a new ICDict with isChanged property set to that of d.

    Method d.fromkeys(seq) will return a new ICDict with isChanged = False.
    """

    def __init__(self, iterable=[], isChanged = False):
        self._nkey = 0
        self._isChanged = False
        if type(iterable) is list:
            self.data = {}
            self.extend(iterable)
        else:
            self.data = dict(iterable)
        self._isChanged = bool(isChanged)

        
    @property
    def isChanged(self):
        "The property for tracking if the ICDict has changed. Accepts only Boolean values"
        return self._isChanged

    @isChanged.setter
    def isChanged(self, value):
        if isinstance(value, bool):
            self._isChanged = value
        else:
            raise TypeError('The value of isChanged must be Boolean, is '+str(type(value)))


    def __getitem__(self, key):
        if type(key) is slice:
            return [self.data.__getitem__(k) for k in range((key.start or 0), (key.stop or len(self.data)), (key.step or 1))]
        else:
            return self.data.__getitem__(key)
    def __setitem__(self, key, value):
        try:
            self.data.__setitem__(key, value)
        except:
            raise
        else:
            self._isChanged = True

    def __delitem__(self, key):
        try:
            self.data.__delitem__(key)
        except:
            raise
        else:
            self._isChanged = True

    def reset(self):
        self.data.clear()
        self._isChanged = True

    def getComplementKeys(self, ids):
        return set(self.data.keys()) - set(ids)
    def getIntersectKeys(self, ids):
        return set(self.data.keys()) & set(ids)

    def getElement(self, i):
        return self.data.get(i, None)
    def deleteElement(self, i):
        if i in self.data:
            del self.data[i] 

    def getIds(self):
        return self.data.keys()

    # Public methods for list
    def append(self, val):
        while self._nkey in self.data:
            self._nkey += 1
        self.data[self._nkey] = val
        self._isChanged = True
        return self._nkey
    
    def extend(self, L):
        if issubclass(type(L), list):
            return [self.append(i) for i in L]
        else:
            return [self.append(i) for k,i in L.items()]
    def insert(self, i, x):
        self.data[i] = x
        self._isChanged = True

    def substitute(self, i, x):
        if i in self:
            self[i] = x
            return True
        return False


    # def remove(self, x):
    #     #### TODO


    def __len__(self):
        return self.data.__len__()

    def __iter__(self):
        return self.data.__iter__()

    def copy(self):
        new = ICDict(self.data)
        new.isChanged = self._isChanged
        new._nkey = self._nkey
        return new

    def has_key(self, key):
        print "has_key() has been deprecated, use 'key in ICDict' instead"
        return key in self.data

    @classmethod
    def fromkeys(cls, seq, value=None):
        new = ICDict()
        new.data = dict.fromkeys(seq, value)
        new.isChanged = False
        return new

    def __repr__(self):
        return 'ICOrdict('+ self.data.__repr__() + ', isChanged=' + str(self._isChanged) + ')'

    def __str__(self):
        return 'ICOrdict: '+ str(self.data)+', isChanged = ' + str(self._isChanged)
        
