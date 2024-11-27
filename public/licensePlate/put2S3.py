import requests
import datetime
import hashlib
import hmac
import os
import configparser
import subprocess

class put2S3:
    def __init__(self, imageName):
        ACCESS_KEY, SECRET_KEY = self.getKeys()
        BUCKET_NAME = 'garage-door-opener.s3.bucket'
        REGION = 'us-east-2'  # Example: 'us-west-2'

        # File details
        file_path = 'testImages/' + imageName
        # object_key = 'testImages/' + imageName
        object_key = 'public/foundPlateImages/' + imageName

        # Read the image file
        with open(file_path, 'rb') as file:
            file_data = file.read()
            payload_hash = hashlib.sha256(file_data).hexdigest()

        # Generate the request URL
        host = f'{BUCKET_NAME}.s3.{REGION}.amazonaws.com'
        url = f'http://{host}/{object_key}'
        print("url = ", url)
        # Current date and time
        current_time = datetime.datetime.utcnow()
        amz_date = current_time.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = current_time.strftime('%Y%m%d')  # Date without time

        # Create headers
        canonical_headers = f'host:{host}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n'
        signed_headers = "host;x-amz-content-sha256;x-amz-date"
        payload_hash = hashlib.sha256(file_data).hexdigest()
        canonical_request = f'PUT\n/{object_key}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}'

        # Create the string to sign
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f'{date_stamp}/{REGION}/s3/aws4_request'
        string_to_sign = f'{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'

        # Calculate the signature
        signing_key = self.generate_signature_key(SECRET_KEY, date_stamp, REGION, 's3')
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        print("Canonical Request:\n", canonical_request)
        print("String to Sign:")
        print(string_to_sign)
        print("Signature:\n", signature)

        # Authorization header
        authorization_header = (
            f'{algorithm} Credential={ACCESS_KEY}/{credential_scope}, '
            f'SignedHeaders={signed_headers}, Signature={signature}'
        )

        headers = {
            "x-amz-content-sha256": payload_hash,
            'x-amz-date': amz_date,
            'Authorization': authorization_header,
            'Content-Type': 'image/jpeg'
        }
        print("header = ")
        print(headers)
        # Make the PUT request
        response = requests.put(url, data=file_data, headers=headers)

        print("response = ", response)

        # Check the response
        if response.status_code == 200:
            print('Image uploaded successfully.')
        else:
            print('Failed to upload image:', response.status_code, response.text)


    def generate_signature_key(self, key, date_stamp, region_name, service_name):
        k_date = hmac.new(('AWS4' + key).encode('utf-8'), date_stamp.encode('utf-8'), hashlib.sha256).digest()
        k_region = hmac.new(k_date, region_name.encode('utf-8'), hashlib.sha256).digest()
        k_service = hmac.new(k_region, service_name.encode('utf-8'), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, 'aws4_request'.encode('utf-8'), hashlib.sha256).digest()
        return k_signing

    def getKeys(self):
        # Path to the AWS credentials file
        aws_credentials_path = os.path.expanduser('~/.aws/credentials')

        # Read the credentials file
        config = configparser.ConfigParser()
        config.read(aws_credentials_path)

        # Specify the profile name (default profile in this case)
        profile_name = 'default'

        if profile_name in config:
            access_key = config[profile_name]['aws_access_key_id_2']
            secret_key = config[profile_name]['aws_secret_access_key_2']
            
            print("Access Key:", access_key)
            print("Secret Key:", secret_key)
        else:
            print(f"Profile '{profile_name}' not found in {aws_credentials_path}")
        
        return access_key, secret_key

put2S3("blankTest.jpeg")