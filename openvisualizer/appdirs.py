#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2005-2010 ActiveState Software Inc.
# Copyright (c) 2013 Eddy Petrișor

# OpenVisualizer copied appdirs from GitHub on commit:
#    https://github.com/ActiveState/appdirs/commit/d033b3dfaab7eb59384f1b73ae5ce6c75d43b684
# Modified site config on Linux to always answer /etc. Don't understand
# use of /etc/xdg.

"""
Utilities for determining application-specific dirs.
See <http://github.com/ActiveState/appdirs> for details and usage.
"""

# Dev Notes:
# - MSDN on where to store app data files:
#   http://support.microsoft.com/default.aspx?scid=kb;en-us;310294#XSLTH3194121123120121120120
# - Mac OS X: http://developer.apple.com/documentation/MacOSX/Conceptual/BPFileSystem/index.html
# - XDG spec for Un*x: http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html

__version_info__ = (1, 3, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
import sys

PY3 = sys.version_info[0] == 3

if PY3:
    unicode = str


def user_data_dir(app_name=None, app_author=None, version=None, roaming=False):
    """
    Return full path to the user-specific data dir for this application.

    :param app_name: is the name of application. If None, just the system directory is returned.
    :param app_author: only required and used on Windows. It is the name of the app_author or distributing body for this
    application. Typically it is the owning company name. This falls back to app_name.

    :param version: is an optional version path element to append to the path. You might want to use this if you want
    multiple versions of your app to be able to run independently. If used, this would typically be "<major>.<minor>".
    Only applied when app_name is present.

    :param roaming: (boolean, default False) can be set True to use the Windows roaming appdata directory.
    That means that for users on a Windows network setup for roaming profiles, this user data will be sync'd on login.
    See <http://technet.microsoft.com/en-us/library/cc766489(WS.10).aspx> for a discussion of issues.

    Typical user data directories are:
        Mac OS X:               ~/Library/Application Support/<AppName>
        Unix:                   ~/.local/share/<AppName>    # or in $XDG_DATA_HOME, if defined
        Win XP (not roaming):   C:\Documents and Settings\<username>\Application Data\<AppAuthor>\<AppName>
        Win XP (roaming):       C:\Documents and Settings\<username>\Local Settings\Application Data\<AppAuthor>\<AppName>
        Win 7  (not roaming):   C:\Users\<username>\AppData\Local\<AppAuthor>\<AppName>
        Win 7  (roaming):       C:\Users\<username>\AppData\Roaming\<AppAuthor>\<AppName>

    For Unix, we follow the XDG spec and support $XDG_DATA_HOME. That means, by default "~/.local/share/<AppName>".
    """

    if sys.platform == "win32":
        if app_author is None:
            app_author = app_name
        const = roaming and "CSIDL_APPDATA" or "CSIDL_LOCAL_APPDATA"
        path = os.path.normpath(_get_win_folder(const))
        if app_name:
            path = os.path.join(path, app_author, app_name)
    elif sys.platform == 'darwin':
        path = os.path.expanduser('~/Library/Application Support/')
        if app_name:
            path = os.path.join(path, app_name)
    else:
        path = os.getenv('XDG_DATA_HOME', os.path.expanduser("~/.local/share"))
        if app_name:
            path = os.path.join(path, app_name)
    if app_name and version:
        path = os.path.join(path, version)
    return path


def site_data_dir(app_name=None, app_author=None, version=None, multipath=False):
    """
    Return full path to the user-shared data dir for this application.

    :param app_name: is the name of application. If None, just the system directory is returned.
    :param app_author: (only required and used on Windows) is the name of the app_author or distributing body for this
    application. Typically it is the owning company name. This falls back to app_name.

    :param version: an optional version path element to append to the path. You might want to use this if you want
    multiple versions of your app to be able to run independently. If used, this would typically be "<major>.<minor>".
    Only applied when app_name is present.

    :param multipath: an optional parameter only applicable to *nix which indicates that the entire list of data dirs
    should be returned. By default, the first item from XDG_DATA_DIRS is returned, or '/usr/local/share/<AppName>',
    if XDG_DATA_DIRS is not set

    Typical user data directories are:
        Mac OS X:   /Library/Application Support/<AppName>
        Unix:       /usr/local/share/<AppName> or /usr/share/<AppName>
        Win XP:     C:\Documents and Settings\All Users\Application Data\<AppAuthor>\<AppName>
        Vista:      (Fail! "C:\ProgramData" is a hidden *system* directory on Vista.)
        Win 7:      C:\ProgramData\<AppAuthor>\<AppName>   # Hidden, but writeable on Win 7.

    For Unix, this is using the $XDG_DATA_DIRS[0] default.

    WARNING: Do not use this on Windows. See the Vista-Fail note above for why.
    """

    if sys.platform == "win32":
        if app_author is None:
            app_author = app_name
        path = os.path.normpath(_get_win_folder("CSIDL_COMMON_APPDATA"))
        if app_name:
            path = os.path.join(path, app_author, app_name)
    elif sys.platform == 'darwin':
        path = os.path.expanduser('/Library/Application Support')
        if app_name:
            path = os.path.join(path, app_name)
    else:
        # XDG default for $XDG_DATA_DIRS
        # only first, if multipath is False
        path = os.getenv('XDG_DATA_DIRS',
                         os.pathsep.join(['/usr/local/share', '/usr/share']))
        path_list = [os.path.expanduser(x.rstrip(os.sep)) for x in path.split(os.pathsep)]
        if app_name:
            if version:
                app_name = os.path.join(app_name, version)
            path_list = [os.sep.join([x, app_name]) for x in path_list]

        if multipath:
            path = os.pathsep.join(path_list)
        else:
            path = path_list[0]
        return path

    if app_name and version:
        path = os.path.join(path, version)
    return path


def user_config_dir(app_name=None, app_author=None, version=None, roaming=False):
    """
    Return full path to the user-specific data dir for this application.

    :param app_name: is the name of application. If None, just the system directory is returned.
    :param app_author: only required and used on Windows. It is the name of the app_author or distributing body for this
    application. Typically it is the owning company name. This falls back to app_name.

    :param version: is an optional version path element to append to the path. You might want to use this if you want
    multiple versions of your app to be able to run independently. If used, this would typically be "<major>.<minor>".
    Only applied when app_name is present.

    :param roaming: (boolean, default False) can be set True to use the Windows roaming appdata directory.
    That means that for users on a Windows network setup for roaming profiles, this user data will be sync'd on login.
    See <http://technet.microsoft.com/en-us/library/cc766489(WS.10).aspx> for a discussion of issues.

    Typical user data directories are:
        Mac OS X:               same as user_data_dir
        Unix:                   ~/.config/<AppName>     # or in $XDG_CONFIG_HOME, if defined
        Win *:                  same as user_data_dir

    For Unix, we follow the XDG spec and support $XDG_DATA_HOME. That means, by default "~/.local/share/<AppName>".
    """

    if sys.platform in ["win32", "darwin"]:
        path = user_data_dir(app_name, app_author, None, roaming)
    else:
        path = os.getenv('XDG_CONFIG_HOME', os.path.expanduser("~/.config"))
        if app_name:
            path = os.path.join(path, app_name)
    if app_name and version:
        path = os.path.join(path, version)
    return path


def site_config_dir(app_name=None, app_author=None, version=None, multipath=False):
    """
    Return full path to the user-shared data dir for this application.

    :param app_name: the name of application. If None, just the system directory is returned.
    :param app_author: (only required and used on Windows) is the name of the app_author or distributing body for this
     application. Typically it is the owning company name. This falls back to app_name.

    :param version: an optional version path element to append to the path. You might want to use this if you want
    multiple versions of your app to be able to run independently. If used, this would typically be "<major>.<minor>".
    Only applied when app_name is present.

    :param multipath: an optional parameter only applicable to *nix which indicates that the entire list of config dirs
    should be returned. By default, the first item from XDG_CONFIG_DIRS is returned, or '/etc/xdg/<AppName>', if
    XDG_CONFIG_DIRS is not set

    Typical user data directories are:
        Mac OS X:   same as site_data_dir
        Unix:       /etc/<AppName> or $XDG_CONFIG_DIRS[i]/<AppName> for each value in
                    $XDG_CONFIG_DIRS
        Win *:      same as site_data_dir
        Vista:      (Fail! "C:\ProgramData" is a hidden *system* directory on Vista.)

    For Unix, this is using the $XDG_CONFIG_DIRS[0] default, if multipath=False

    WARNING: Do not use this on Windows. See the Vista-Fail note above for why.
    """

    if sys.platform in ["win32", "darwin"]:
        path = site_data_dir(app_name, app_author)
        if app_name and version:
            path = os.path.join(path, version)
    else:
        # XDG default for $XDG_CONFIG_DIRS
        # only first, if multipath is False
        # path = os.getenv('XDG_CONFIG_DIRS', '/etc/xdg')
        path = '/etc'
        path_list = [os.path.expanduser(x.rstrip(os.sep)) for x in path.split(os.pathsep)]
        if app_name:
            if version:
                app_name = os.path.join(app_name, version)
            path_list = [os.sep.join([x, app_name]) for x in path_list]

        if multipath:
            path = os.pathsep.join(path_list)
        else:
            path = path_list[0]
    return path


def user_cache_dir(app_name=None, app_author=None, version=None, opinion=True):
    """
    Return full path to the user-specific cache dir for this application.

    :param app_name: the name of application. If None, just the system directory is returned.
    :param app_author: (only required and used on Windows) is the name of the app_author or distributing body for this
    application. Typically it is the owning company name. This falls back to app_name.

    :param version: an optional version path element to append to the path. You might want to use this if you want
    multiple versions of your app to be able to run independently. If used, this would typically be "<major>.<minor>".
    Only applied when app_name is present.

    :param opinion: (boolean) can be False to disable the appending of "Cache" to the base app data dir for Windows. See
    discussion below.

    Typical user cache directories are:
        Mac OS X:   ~/Library/Caches/<AppName>
        Unix:       ~/.cache/<AppName> (XDG default)
        Win XP:     C:\Documents and Settings\<username>\Local Settings\Application Data\<AppAuthor>\<AppName>\Cache
        Vista:      C:\Users\<username>\AppData\Local\<AppAuthor>\<AppName>\Cache

    On Windows the only suggestion in the MSDN docs is that local settings go in the `CSIDL_LOCAL_APPDATA` directory.
    This is identical to the non-roaming app data dir (the default returned by `user_data_dir` above). Apps typically
    put cache data somewhere *under* the given dir here. Some examples:
        ...\Mozilla\Firefox\Profiles\<ProfileName>\Cache
        ...\Acme\SuperApp\Cache\1.0

    OPINION: This function appends "Cache" to the `CSIDL_LOCAL_APPDATA` value. This can be disabled with the
    `opinion=False` option.
    """

    if sys.platform == "win32":
        if app_author is None:
            app_author = app_name
        path = os.path.normpath(_get_win_folder("CSIDL_LOCAL_APPDATA"))
        if app_name:
            path = os.path.join(path, app_author, app_name)
            if opinion:
                path = os.path.join(path, "Cache")
    elif sys.platform == 'darwin':
        path = os.path.expanduser('~/Library/Caches')
        if app_name:
            path = os.path.join(path, app_name)
    else:
        path = os.getenv('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))
        if app_name:
            path = os.path.join(path, app_name)
    if app_name and version:
        path = os.path.join(path, version)
    return path


def user_log_dir(app_name=None, app_author=None, version=None, opinion=True):
    """
    Return full path to the user-specific log dir for this application.

    :param app_name: the name of application. If None, just the system directory is returned.
    :param app_author: (only required and used on Windows) is the name of the app_author or distributing body for this
    application. Typically it is the owning company name. This falls back to app_name.

    :param version: an optional version path element to append to the path. You might want to use this if you want
    multiple versions of your app to be able to run independently. If used, this would typically be "<major>.<minor>".
    Only applied when app_name is present.

    :param opinion: (boolean) can be False to disable the appending of "Logs" to the base app data dir for Windows,
    and "log" to the base cache dir for Unix. See discussion below.

    Typical user cache directories are:
        Mac OS X:   ~/Library/Logs/<AppName>
        Unix:       ~/.cache/<AppName>/log  # or under $XDG_CACHE_HOME if defined
        Win XP:     C:\Documents and Settings\<username>\Local Settings\Application Data\<AppAuthor>\<AppName>\Logs
        Vista:      C:\Users\<username>\AppData\Local\<AppAuthor>\<AppName>\Logs

    On Windows the only suggestion in the MSDN docs is that local settings go in the `CSIDL_LOCAL_APPDATA` directory.
    (Note: I'm interested in examples of what some windows apps use for a logs dir.)

    OPINION: This function appends "Logs" to the `CSIDL_LOCAL_APPDATA`
    value for Windows and appends "log" to the user cache dir for Unix.
    This can be disabled with the `opinion=False` option.
    """

    if sys.platform == "darwin":
        path = os.path.join(
            os.path.expanduser('~/Library/Logs'),
            app_name)
    elif sys.platform == "win32":
        path = user_data_dir(app_name, app_author, version)
        version = False
        if opinion:
            path = os.path.join(path, "Logs")
    else:
        path = user_cache_dir(app_name, app_author, version)
        version = False
        if opinion:
            path = os.path.join(path, "log")
    if app_name and version:
        path = os.path.join(path, version)
    return path


class AppDirs(object):
    """Convenience wrapper for getting application dirs."""

    def __init__(self, app_name, app_author=None, version=None,
                 roaming=False, multipath=False):
        self.app_name = app_name
        self.app_author = app_author
        self.version = version
        self.roaming = roaming
        self.multipath = multipath

    @property
    def user_data_dir(self):
        return user_data_dir(self.app_name, self.app_author, version=self.version, roaming=self.roaming)

    @property
    def site_data_dir(self):
        return site_data_dir(self.app_name, self.app_author, version=self.version, multipath=self.multipath)

    @property
    def user_config_dir(self):
        return user_config_dir(self.app_name, self.app_author, version=self.version, roaming=self.roaming)

    @property
    def site_config_dir(self):
        return site_data_dir(self.app_name, self.app_author, version=self.version, multipath=self.multipath)

    @property
    def user_cache_dir(self):
        return user_cache_dir(self.app_name, self.app_author, version=self.version)

    @property
    def user_log_dir(self):
        return user_log_dir(self.app_name, self.app_author, version=self.version)


# ---- internal support stuff

def _get_win_folder_from_registry(csidl_name):
    """
    This is a fallback technique at best. I'm not sure if using the registry for this guarantees us the correct answer
    for all CSIDL_* names.
    """

    import _winreg

    shell_folder_name = {
        "CSIDL_APPDATA": "AppData",
        "CSIDL_COMMON_APPDATA": "Common AppData",
        "CSIDL_LOCAL_APPDATA": "Local AppData",
    }[csidl_name]

    key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,
                          r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
    directory, type = _winreg.QueryValueEx(key, shell_folder_name)
    return directory


def _get_win_folder_with_pywin32(csidl_name):
    from win32com.shell import shellcon, shell
    directory = shell.SHGetFolderPath(0, getattr(shellcon, csidl_name), 0, 0)

    # Try to make this a unicode path because SHGetFolderPath does
    # not return unicode strings when there is unicode data in the
    # path.
    try:
        directory = unicode(directory)

        # Downgrade to short path name if have highbit chars. See
        # <http://bugs.activestate.com/show_bug.cgi?id=85099>.
        has_high_char = False
        for c in directory:
            if ord(c) > 255:
                has_high_char = True
                break
        if has_high_char:
            try:
                import win32api
                directory = win32api.GetShortPathName(directory)
            except ImportError:
                pass
    except UnicodeError:
        pass
    return directory


def _get_win_folder_with_ctypes(csidl_name):
    import ctypes

    csidl_const = {
        "CSIDL_APPDATA": 26,
        "CSIDL_COMMON_APPDATA": 35,
        "CSIDL_LOCAL_APPDATA": 28,
    }[csidl_name]

    buf = ctypes.create_unicode_buffer(1024)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl_const, None, 0, buf)

    # Downgrade to short path name if have highbit chars. See
    # <http://bugs.activestate.com/show_bug.cgi?id=85099>.
    has_high_char = False
    for c in buf:
        if ord(c) > 255:
            has_high_char = True
            break
    if has_high_char:
        buf2 = ctypes.create_unicode_buffer(1024)
        if ctypes.windll.kernel32.GetShortPathNameW(buf.value, buf2, 1024):
            buf = buf2

    return buf.value


if sys.platform == "win32":
    try:
        import win32com.shell

        _get_win_folder = _get_win_folder_with_pywin32
    except ImportError:
        try:
            import ctypes

            _get_win_folder = _get_win_folder_with_ctypes
        except ImportError:
            _get_win_folder = _get_win_folder_from_registry

# ---- self test code

if __name__ == "__main__":
    name = "MyApp"
    author = "MyCompany"

    props = ("user_data_dir", "site_data_dir",
             "user_config_dir", "site_config_dir",
             "user_cache_dir", "user_log_dir")

    print("-- app dirs (with optional 'version')")
    dirs = AppDirs(name, author, version="1.0")
    for prop in props:
        print("%s: %s" % (prop, getattr(dirs, prop)))

    print("\n-- app dirs (without optional 'version')")
    dirs = AppDirs(name, author)
    for prop in props:
        print("%s: %s" % (prop, getattr(dirs, prop)))

    print("\n-- app dirs (without optional 'app_author')")
    dirs = AppDirs(name)
    for prop in props:
        print("%s: %s" % (prop, getattr(dirs, prop)))
