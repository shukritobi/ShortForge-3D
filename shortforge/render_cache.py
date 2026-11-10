"""Conservative shot fingerprints: persistent construction propagates forward.

Narration, captions and SFX never invalidate geometry. Earlier visual edits
invalidate following shots because objects and camera state persist.
"""
import hashlib
import json
import struct
import zlib
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def shot_keys(story, engine):
    prefix=[]
    result=[]
    for beat in story["beats"]:
        prefix.append({k:beat[k] for k in ("id","start","end","actions","camera")})
        result.append(digest([engine,story["scene_template"],story["fps"],story["resolution"],prefix]))
    return result


def valid_png(path, resolution):
    """Verify chunk CRCs, dimensions and complete compressed pixel data."""
    try:
        data=Path(path).read_bytes()
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            return False
        pos=8
        compressed=bytearray()
        dimensions=None
        channels=None
        while pos+12<=len(data):
            size=struct.unpack(">I",data[pos:pos+4])[0]
            kind=data[pos+4:pos+8]
            body=data[pos+8:pos+8+size]
            crc=data[pos+8+size:pos+12+size]
            if len(crc)!=4 or zlib.crc32(kind+body) != struct.unpack(">I",crc)[0]:
                return False
            if kind==b"IHDR":
                dimensions=struct.unpack(">II",body[:8])
                if len(body)!=13 or body[8]!=8 or body[12]!=0:return False
                channels={0:1,2:3,4:2,6:4}.get(body[9])
            if kind==b"IDAT":
                compressed.extend(body)
            if kind==b"IEND":
                return (dimensions==tuple(resolution) and channels is not None and
                        len(zlib.decompress(compressed))==dimensions[1]*(1+dimensions[0]*channels))
            pos+=size+12
    except (OSError,ValueError,zlib.error,struct.error):
        return False
    return False
