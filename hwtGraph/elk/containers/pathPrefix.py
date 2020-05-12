
def pathPrefixApply(path_prefix, o):
    if path_prefix is None:
        return o
    elif isinstance(path_prefix, tuple):
        return (*path_prefix, o)
    else:
        return (path_prefix, o)
