import os, shutil

def copyTree(src, dst, symlinks=False, ignore=None):
    """ Copy all files from one to another directory

    Args:
        src (_type_): Source directory, From
        dst (_type_): Destination directory, To
        symlinks (bool, optional): _description_. Defaults to False.
        ignore (_type_, optional): _description_. Defaults to None.
    """

    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)