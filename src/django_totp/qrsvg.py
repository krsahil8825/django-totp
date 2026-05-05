"""Render TOTP provisioning data as inline SVG QR codes."""

from io import BytesIO

import qrcode
from qrcode.image.svg import SvgImage


def render_qr_code_svg(data: str) -> str:
    """Build a QR code SVG string for the provided provisioning payload."""

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
