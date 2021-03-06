'''Exceptions used by the FlickrAPI module.'''

class IllegalArgumentException(ValueError):
    '''Raised when a method is passed an illegal argument.
    
    More specific details will be included in the exception message
    when thrown.
    '''

class FlickrError(Exception):
    '''Raised when a Flickr method fails.
    
    More specific details will be included in the exception message
    when thrown.
    '''
