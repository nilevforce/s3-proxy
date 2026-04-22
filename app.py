from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse, JSONResponse

import boto3

from botocore.exceptions import ClientError
from cuid2 import cuid_wrapper

app = FastAPI()

create_cuid = cuid_wrapper()

# ---------------- S3 CLIENT ----------------

def get_s3_client(access, secret, endpoint, region=None):
    return boto3.client(
        "s3",
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        endpoint_url=endpoint,
        region_name=region or "us-east-1",
    )


# ---------------- HEADERS DEPENDENCY ----------------

def get_headers(
    x_s3_access_key: str = Header(...),
    x_s3_secret_key: str = Header(...),
    x_s3_endpoint: str = Header(...),
    x_s3_bucket: str = Header(...),
    x_s3_region: str = Header(None),
):
    return {
        "access": x_s3_access_key,
        "secret": x_s3_secret_key,
        "endpoint": x_s3_endpoint,
        "bucket": x_s3_bucket,
        "region": x_s3_region,
    }


# ---------------- ERROR HANDLING ----------------

def handle_s3_error(e: ClientError):
    code = e.response["Error"]["Code"]

    if code in ["NoSuchKey", "404"]:
        raise HTTPException(404, "File not found")

    if code in ["AccessDenied"]:
        raise HTTPException(403, "Access denied")

    if code in ["InvalidAccessKeyId", "SignatureDoesNotMatch"]:
        raise HTTPException(401, "Invalid S3 credentials")

    raise HTTPException(500, f"S3 error: {code}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "detail": str(exc),
        },
    )


# ---------------- UPLOAD ----------------

@app.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    key: str = None,
    h=Depends(get_headers),
):
    client = get_s3_client(
        h["access"], h["secret"], h["endpoint"], h["region"]
    )

    bucket = h["bucket"]

    cuid = create_cuid()
    key = key or f"uploads/{cuid}-{file.filename}"

    try:
        client.upload_fileobj(file.file, bucket, key)
    except ClientError as e:
        handle_s3_error(e)

    return {
        "bucket": bucket,
        "key": key,
        "filename": file.filename,
    }


# ---------------- DOWNLOAD (STREAM) ----------------

@app.get("/files/{key}")
def download_file(key: str, h=Depends(get_headers)):
    client = get_s3_client(
        h["access"], h["secret"], h["endpoint"], h["region"]
    )

    bucket = h["bucket"]

    try:
        obj = client.get_object(Bucket=bucket, Key=key)
    except ClientError as e:
        handle_s3_error(e)

    def stream():
        for chunk in obj["Body"].iter_chunks(1024 * 1024):
            yield chunk

    return StreamingResponse(stream())


# ---------------- DELETE ----------------

@app.delete("/files/{key}")
def delete_file(key: str, h=Depends(get_headers)):
    client = get_s3_client(
        h["access"], h["secret"], h["endpoint"], h["region"]
    )

    bucket = h["bucket"]

    try:
        client.delete_object(Bucket=bucket, Key=key)
    except ClientError as e:
        handle_s3_error(e)

    return {"deleted": True, "key": key}


# ---------------- PRESIGN DOWNLOAD ----------------

@app.get("/files/{key}/presign")
def presign_download(key: str, h=Depends(get_headers)):
    client = get_s3_client(
        h["access"], h["secret"], h["endpoint"], h["region"]
    )

    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": h["bucket"], "Key": key},
            ExpiresIn=3600,
        )
    except ClientError as e:
        handle_s3_error(e)

    return {"url": url, "expires_in": 3600}


# ---------------- PRESIGN UPLOAD ----------------

@app.post("/files/presign-upload")
def presign_upload(
    key: str,
    content_type: str = "application/octet-stream",
    h=Depends(get_headers),
):
    client = get_s3_client(
        h["access"], h["secret"], h["endpoint"], h["region"]
    )

    try:
        url = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": h["bucket"],
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=3600,
        )
    except ClientError as e:
        handle_s3_error(e)

    return {
        "url": url,
        "key": key,
        "expires_in": 3600,
    }
