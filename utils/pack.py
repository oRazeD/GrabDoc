import os
import numpy # pylint: disable=E0401

import bpy

from .io import get_filepath, get_format
from .baker import get_bakers


def pack_image_channels(
        pack_order: list, name: str, size: tuple[int, int]=None
    ) -> bpy.types.Image:
    """NOTE: Original code sourced from:
    https://blender.stackexchange.com/questions/274712/how-to-channel-pack-texture-in-python"""
    # Build the packed pixel array
    w, h = size
    src_array = numpy.empty(w * h * 4, dtype=numpy.float32)
    dst_array = numpy.ones(w * h * 4, dtype=numpy.float32)
    has_alpha = True

    # Fetch pixels from the source image and copy channels
    for pack_item in pack_order:
        image = pack_item[0]
        image.pixels.foreach_get(src_array)
        for src_chan, dst_chan in pack_item[1:]:
            if dst_chan == 3 and image.name == "_gd_pack_temp":
                has_alpha = False
                continue
            dst_array[dst_chan::4] = src_array[src_chan::4]

    # Create image from the packed pixels
    dst_image = bpy.data.images.new(name, w, h, is_data=True, alpha=has_alpha)
    dst_image.pixels.foreach_set(dst_array)
    return dst_image


def get_channel_paths() -> tuple[str, str, str, str]:
    gd = bpy.context.scene.gd
    r = get_channel_path(gd.channel_r)
    g = get_channel_path(gd.channel_g)
    b = get_channel_path(gd.channel_b)
    a = get_channel_path(gd.channel_a)
    return r, g, b, a


def get_channel_path(channel: str) -> str | None:
    """Get the channel path of the given channel name.

    If the channel path is not found returns `None`."""
    if channel == "none":
        return None
    gd = bpy.context.scene.gd
    channel, idx = channel.split('_')
    suffix = getattr(gd, channel)[int(idx)].suffix
    if suffix is None:
        return None
    filename = gd.filename + '_' + suffix + get_format()
    filepath = os.path.join(bpy.path.abspath(get_filepath()), filename)
    if not os.path.exists(filepath):
        return None
    return filepath


def is_pack_maps_enabled() -> bool:
    """Checks if the chosen pack channels
    match the enabled maps to export.

    This function also returns True if a required
    bake map is not enabled but the texture exists."""
    baker_ids  = ['none']
    baker_ids += [f"{baker.ID}_{baker.index}" for baker in get_bakers(filter_enabled=True)]
    r, g, b, a = get_channel_paths()
    gd = bpy.context.scene.gd
    print(gd.channel_r, gd.channel_g, gd.channel_b, gd.channel_a)
    print(baker_ids)
    if gd.channel_r not in baker_ids and r is None:
        return False
    if gd.channel_g not in baker_ids and g is None:
        return False
    if gd.channel_b not in baker_ids and b is None:
        return False
    if gd.channel_a not in baker_ids and a is None:
        return False
    return True
