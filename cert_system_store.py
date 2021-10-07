#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# https://blog.darrenjrobinson.com/accessing-the-windows-certificate-store-using-python/

import base64
import os
import ssl

import slugify as unicode_slug
import wincertstore
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

# from cryptography.x509.oid import ExtensionOID


def hex_string_readable(bytes):
    return ["{:02X}".format(x) for x in bytes]


def slugify(text, separator="_"):
    """Slugify a given text."""
    if text == "" or text is None:
        return ""
    slug = unicode_slug.slugify(text, separator=separator)
    return "unknown" if slug == "" else slug


if os.name == "nt":
    cnt = 0
    for storename in ("ROOT", "CA", "MY"):
        with wincertstore.CertSystemStore(storename) as store:
            for cert in store.itercerts(usage=wincertstore.SERVER_AUTH):

                pem = cert.get_pem()
                encoded_der = "".join(pem.split("\n")[1:-2])

                cert_bytes = base64.b64decode(encoded_der)
                cert_pem = ssl.DER_cert_to_PEM_cert(cert_bytes)
                cert_details = x509.load_pem_x509_certificate(cert_pem.encode("utf-8"), default_backend())

                fingerprint = hex_string_readable(cert_details.fingerprint(hashes.SHA1()))
                fingerprint_string = "".join(fingerprint)

                print(cert.get_name())
                print("     Issuer: ", cert_details.issuer.rfc4514_string())
                print("     Thumbprint: ", fingerprint_string.lower())
                print("     Subject: ", cert_details.subject.rfc4514_string())
                print("     Serial Number: ", hex(cert_details.serial_number).replace("0x", ""))
                print("     Issued (UTC): ", cert_details.not_valid_before)
                print("     Expiry (UTC): ", cert_details.not_valid_after)

                # san = cert_details.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
                # names = san.get_values_for_type(x509.DNSName)
                # print("     SAN(s): ", names)

                # cert_usages = cert_details.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE).value._usages
                # print("     Usage(s): ", cert_usages)

                # write .cer file
                with open(f"{slugify(cert.get_name())}.cer", "wb") as f:
                    f.write(cert_bytes)

                print()
                cnt += 1

    print(f"Successfully exported {cnt} certificates.")
else:
    print("This only works on a Windows System.")
