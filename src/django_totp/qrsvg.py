"""
django_totp.qrsvg
=================

This is a helper function to generate QR codes in svg format and
return the svg code/content as a string. This make it easier to
respond with json response and embed the svg directly in the frontend
without needing to save the svg as a file or serve it as a separate endpoint.
"""

from qrcode.image.svg import SvgImage
from io import BytesIO
import qrcode


def generate_qr_code_svg(data: str) -> str:
    """
    Generate a QR code in SVG format for the given data.

    Args:
        data (str): The data to encode in the QR code.

    Returns:
        str: The SVG representation of the QR code.
    """
    qr = qrcode.QRCode(version=1, box_size=10, border=4, image_factory=SvgImage)
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(
        attrib={
            "fill": "black",
            "style": "background-color:white",
        }
    )

    stream = BytesIO()
    img.save(stream)

    return stream.getvalue().decode("utf-8")
