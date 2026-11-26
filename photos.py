"""Decode actual image content, remove metadata, and store bounded JPEGs."""
import base64
import binascii
from io import BytesIO
import warnings

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_ENCODED_LENGTH = 4 * ((MAX_PHOTO_BYTES + 2) // 3)
MAX_PIXELS = 20_000_000


def prepare_photo(encoded):
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(422, 'Photo data is invalid') from None
    if len(raw) > MAX_PHOTO_BYTES:
        raise HTTPException(413, 'Each photo must be 5 MB or smaller')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as source:
                if source.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise HTTPException(422, 'Use JPEG, PNG, or WebP photos')
                if source.width * source.height > MAX_PIXELS:
                    raise HTTPException(422, 'Photo exceeds 20 megapixels')
                if getattr(source, 'n_frames', 1) > 1:
                    raise HTTPException(422, 'Use a still photo, not an animated image')
                source.load()
                oriented = ImageOps.exif_transpose(source)
                oriented.thumbnail((1600, 1600))
                rgba = oriented.convert('RGBA')
                # A fresh canvas drops EXIF, GPS, and other source metadata.
                clean = Image.new('RGB', rgba.size, 'white')
                clean.paste(rgba, mask=rgba.getchannel('A'))
                output = BytesIO()
                clean.save(output, format='JPEG', quality=85, optimize=True)
                return output.getvalue()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(422, 'Could not read this photo. Use a valid JPEG, PNG, or WebP image.') from None
