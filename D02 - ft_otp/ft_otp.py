#!/usr/bin/python3

import time
import base64
import argparse
import rsa
import os
import struct
import qrcode
import qrcode.image.svg

def left_rotate(n, b):
    return ((n << b) | (n >> (32 - b))) & 0xFFFFFFFF

def sha1(data):
    # Pre-processing: Padding the message
    original_byte_len = len(data)
    original_bit_len = original_byte_len * 8
    
    # Append the bit '1' to the message
    data += b'\x80'
    
    # Append 0 <= k < 512 bits '0', so that the resulting message length (in bits)
    # is congruent to 448 (mod 512)
    while (len(data) * 8) % 512 != 448:
        data += b'\x00'

    # Append original length in bits mod 2^64 to message
    data += struct.pack('>Q', original_bit_len)
    
    # Process the message in successive 512-bit chunks
    h0, h1, h2, h3, h4 = (0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0)
    
    for i in range(0, len(data), 64):
        w = [0] * 80
        for j in range(16):
            w[j] = struct.unpack('>I', data[i + j*4:i + j*4 + 4])[0]
        for j in range(16, 80):
            w[j] = left_rotate(w[j-3] ^ w[j-8] ^ w[j-14] ^ w[j-16], 1)
        
        a, b, c, d, e = h0, h1, h2, h3, h4
        
        for j in range(80):
            if 0 <= j <= 19:
                f = (b & c) | ((~b) & d)
                k = 0x5A827999
            elif 20 <= j <= 39:
                f = b ^ c ^ d
                k = 0x6ED9EBA1
            elif 40 <= j <= 59:
                f = (b & c) | (b & d) | (c & d)
                k = 0x8F1BBCDC
            elif 60 <= j <= 79:
                f = b ^ c ^ d
                k = 0xCA62C1D6
            
            temp = (left_rotate(a, 5) + f + e + k + w[j]) & 0xFFFFFFFF
            e = d
            d = c
            c = left_rotate(b, 30)
            b = a
            a = temp
        
        h0 = (h0 + a) & 0xFFFFFFFF
        h1 = (h1 + b) & 0xFFFFFFFF
        h2 = (h2 + c) & 0xFFFFFFFF
        h3 = (h3 + d) & 0xFFFFFFFF
        h4 = (h4 + e) & 0xFFFFFFFF
    
    return struct.pack('>5I', h0, h1, h2, h3, h4)

def hmac_sha1(key, message):
    block_size = 64  # Block size for SHA-1
    
    if len(key) > block_size:
        key = sha1(key)  # Keys longer than block size are shortened by hashing them
    if len(key) < block_size:
        key += b'\x00' * (block_size - len(key))  # Keys shorter than block size are zero-padded
    
    o_key_pad = bytes([k ^ 0x5C for k in key])
    i_key_pad = bytes([k ^ 0x36 for k in key])

    return sha1(o_key_pad + sha1(i_key_pad + message))


def hotp(key, counter, digits=6):
    hmac_result = hmac_sha1(key, struct.pack('>Q', counter))
    offset = hmac_result[-1] & 0x0F
    binary_code = struct.unpack('>I', hmac_result[offset:offset + 4])[0] & 0x7FFFFFFF
    otp = binary_code % (10 ** digits)
    return str(otp).zfill(digits)

def totp(key, time_step=30, digits=6, t0=0):
    current_time = int(time.time())
    time_counter = (current_time - t0) // time_step
    key_bytes = base64.b16decode(key, casefold=True)
    return hotp(key_bytes, time_counter, digits)

def generate_qr_code():
    secret_key = os.urandom(32)
    secret_key_b16 = secret_key.hex()
    secret_key = base64.b32encode(secret_key).decode()
    print(f"Secret key b32: {secret_key}")
    img = qrcode.make("otpauth://totp/ft_otp?secret=" + secret_key, image_factory=qrcode.image.svg.SvgImage)
    try:
        os.makedirs('qr_codes', exist_ok=True)
    except Exception as e:
        print(f"Error creating directory: {e}")
        exit()
    img.save('qr_codes/qr.svg')
    print(f"Secret key: {secret_key_b16}")
    return secret_key_b16


parser = argparse.ArgumentParser(description='Creates a one time password using the TOTP algorithm.')

parser.add_argument('-g', '--generate', nargs='?', type=str, const="QR", help='Encrypts secret key and stores it in a file.')
parser.add_argument('-k', '--key', nargs='?',type=str, const="ft_otp.key", help='Reads secret key from a file and generates OTP')
parser.add_argument('-c', '--clear', action='store_true', help='Clears the rsa_keys directory and ft_otp.key')

args = parser.parse_args()

generate = args.generate
key = args.key
clear = args.clear

if not generate and not key and not clear:
    print("Please provide a secret key or generate one.")
    exit()

if generate:
    if generate == "QR" or generate == "qr":
        try :
            with open('qr_codes/qr.svg', 'r') as f:
                print("QR code already generated.")
                exit()
        except FileNotFoundError:
            secret_key = generate_qr_code()
    else:
        try:
            with open(generate, 'r') as f:
                secret_key = f.read()
        except FileNotFoundError:
            print(f"File {generate} not found.")
            exit()
        except Exception as e:
            print(f"Error reading file: {e}")
            exit()
    if len(secret_key) < 64:
        print("Secret key must be 64 characters long.")
        exit()
    elif len(secret_key) > 128:
        print("Secret key must be less than 128 characters long.")
        exit()
    elif not all(c in '0123456789ABCDEF' for c in secret_key.upper()):
        print("Secret key must be a hex string.")
        exit()
    elif len(secret_key) % 2 != 0:
        print("Secret key must be a hex string.")
        exit()
    public_key, private_key = rsa.newkeys(2048)
    try:
        os.makedirs('rsa_keys', exist_ok=True)
    except Exception as e:
        print(f"Error creating directory: {e}")
        exit()
    try:
        with open('rsa_keys/ft_otp.pub', 'w') as f:
            f.write(public_key.save_pkcs1().decode())
        with open('rsa_keys/ft_otp.priv', 'w') as f:
            f.write(private_key.save_pkcs1().decode())
        encmessage = rsa.encrypt(secret_key.encode(), public_key)
        with open('ft_otp.key', 'wb') as f:
            f.write(encmessage)
    except Exception as e:
        print(f"Error writing keys:{e}")
        exit()

if key:
    try:
        with open(key, 'rb') as f:
            secret_key = f.read()
        with open('rsa_keys/ft_otp.priv', 'r') as f:
            private_key = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        exit()
    private_key = rsa.PrivateKey.load_pkcs1(private_key.encode())
    secret_key = rsa.decrypt(secret_key, private_key).decode()
    otp = totp(secret_key)
    print(f'TOTP Value: {otp}')

if clear:
    try:
        os.remove('ft_otp.key')
        os.remove('rsa_keys/ft_otp.pub')
        os.remove('rsa_keys/ft_otp.priv')
        os.rmdir('rsa_keys')
        os.remove('qr_codes/qr.svg')
        os.rmdir('qr_codes')
    except Exception as e:
        print(f"Error clearing keys: {e}")
        exit()
    print("Keys cleared.")