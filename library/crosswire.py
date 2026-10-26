"""Fetch and open CrossWire SWORD modules, and describe their license terms."""

import os
import zipfile

from library.fetch import RAW_DIR, fetch
from library.sword import open_module

RAWZIP = "https://www.crosswire.org/ftpmirror/pub/sword/packages/rawzip/"
MODULE_PAGE = "https://www.crosswire.org/sword/modules/ModInfo.jsp?modName="


def get_module(name):
    """Download (if needed) and extract a module; return (fetched, conf, reader)."""
    fetched = fetch(RAWZIP + name + ".zip", "crosswire")
    dest = os.path.join(RAW_DIR, "crosswire", "x", name)
    if not os.path.isdir(os.path.join(dest, "mods.d")):
        with zipfile.ZipFile(fetched["path"]) as z:
            # Only extract regular relative paths (downloaded archives are untrusted).
            for member in z.namelist():
                if member.startswith("/") or ".." in member.split("/"):
                    raise ValueError(f"unsafe path in {name}.zip: {member}")
            z.extractall(dest)
    conf_name = [f for f in os.listdir(os.path.join(dest, "mods.d")) if f.endswith(".conf")][0]
    section, conf, reader = open_module(dest, conf_name)
    return fetched, conf, reader


def license_evidence(name, conf):
    def first(k):
        return (conf.get(k) or [""])[0]
    parts = [f"CrossWire module '{name}' v{first('Version')}: DistributionLicense={first('DistributionLicense')}"]
    if first("TextSource"):
        parts.append(f"TextSource={first('TextSource')}")
    about = first("About")
    if about:
        parts.append("About: " + about.replace("\\par", " ").strip()[:400])
    return ". ".join(parts)


def edition(name, conf):
    def first(k):
        return (conf.get(k) or [""])[0]
    return (f"CrossWire SWORD module {name} version {first('Version')} "
            f"({first('ModDrv')}, {first('SourceType') or 'plain'} markup)")
