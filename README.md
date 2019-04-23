# PyLudus #

A python interface for operating [ludus](https://github.com/kaniblu/ludus-jluva).

Install this package by running `python setup.py install`.

## Example ##

    >>> import pyludus
    >>> ludus = pyludus.Ludus("/home/path/to/ludus")
    
    >>> # equivalent to calling `instance-create default-archetype --overwrite`
    >>> ludus.create_instance("default-archetype", overwrite=True)
    
    >>> # equivalent to calling `instance-run default-archetype`
    >>> ludus.run_instance("default-archtype")
    
    >>> # equivalent to calling `instance-clear -y default-archetype`
    >>> ludus.clear_instance("default-archetype")
    
    >>> # equivalent to calling 
    >>> # `config-set default-archetype config key 3 --type int --write-back`
    >>> ludus.set_config("default-archetype", config, key, 3)
    
    >>> # equivalent to calling
    >>> # `config-get default-archetype config key1 key2`
    >>> ludus.get_config("default-archtype", config, key1, key2)
    ['3.5', '1.5']
