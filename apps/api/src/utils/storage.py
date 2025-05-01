import os

import aioboto3
from botocore.exceptions import ClientError
from src.config import AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION, AWS_SECRET_ACCESS_KEY

BUCKET_NAME: str = "assets.speck.sh"
CORE_PREFIX: str = "core"

session: aioboto3.Session = aioboto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_DEFAULT_REGION,
)


def _get_full_path(path: str, filename: str | None = None) -> str:
    """
    Construct the full S3 key path with the core prefix.

    :param path: The path within the bucket
    :param filename: Optional filename to append to the path
    :return: Full S3 key path including core prefix
    """
    clean_path: str = path.strip("/")
    if filename:
        return f"{CORE_PREFIX}/{clean_path}/{filename}"
    return f"{CORE_PREFIX}/{clean_path}"


async def save_asset(path: str, filename: str, content: str | bytes) -> str:
    """
    Save an asset to S3.

    :param path: The path within the bucket (e.g., "/preview/test-folder")
    :param filename: The name of the file to save
    :param content: The content to save, either as string or bytes
    :return: The URL of the saved asset
    :raises Exception: If the save operation fails
    """
    full_path: str = _get_full_path(path, filename)

    if isinstance(content, str):
        content = content.encode("utf-8")

    try:
        async with session.client("s3") as s3:
            await s3.put_object(
                Bucket=BUCKET_NAME,
                Key=full_path,
                Body=content,
                ContentType=_guess_content_type(filename),
            )
        return f"https://{BUCKET_NAME}/{full_path}"
    except ClientError as e:
        raise ClientError(f"Failed to save asset: {str(e)}")


async def delete_asset(path: str, filename: str) -> None:
    """
    Delete an asset from S3.

    :param path: The path within the bucket
    :param filename: The name of the file to delete
    :raises Exception: If the delete operation fails
    """
    full_path: str = _get_full_path(path, filename)

    try:
        async with session.client("s3") as s3:
            await s3.delete_object(Bucket=BUCKET_NAME, Key=full_path)
    except ClientError as e:
        raise ClientError(f"Failed to delete asset: {str(e)}") from e


async def list_assets(path: str) -> list[str]:
    """
    List all assets in a given path.

    :param path: The path to list assets from
    :return: List of asset filenames in the path
    :raises Exception: If the list operation fails
    """
    full_path: str = _get_full_path(path)

    try:
        async with session.client("s3") as s3:
            response = await s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=full_path)

            files = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    key = obj["Key"]
                    if key != full_path + "/":
                        filename = key.replace(full_path + "/", "")
                        if filename:
                            files.append(filename)
            return files
    except ClientError as e:
        raise ClientError(f"Failed to list assets: {str(e)}") from e


async def read_asset(path: str, filename: str) -> bytes:
    """
    Read an asset from S3.

    :param path: The path within the bucket
    :param filename: The name of the file to read
    :return: The content of the file as bytes
    :raises Exception: If the read operation fails
    """
    full_path: str = _get_full_path(path, filename)

    try:
        async with session.client("s3") as s3:
            response = await s3.get_object(Bucket=BUCKET_NAME, Key=full_path)
            async with response["Body"] as stream:
                return await stream.read()
    except ClientError as e:
        raise ClientError(f"Failed to read asset: {str(e)}") from e


def _guess_content_type(filename: str) -> str:
    """
    Guess the content type based on file extension.

    :param filename: The name of the file
    :return: The guessed MIME type for the file
    """
    ext: str = os.path.splitext(filename)[1].lower()
    content_types: dict[str, str] = {
        ".txt": "text/plain",
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".pdf": "application/pdf",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
    }
    return content_types.get(ext, "application/octet-stream")


if __name__ == "__main__":
    import asyncio

    async def test_storage() -> None:
        """Run a test of all storage operations."""
        try:
            test_content: str = "Idk smtg do"
            url: str = await save_asset(
                "/preview/test-folder", "cock.txt", test_content
            )
            print(f"Saved test file at {url}")

            files: list[str] = await list_assets("/preview/test-folder")
            print(f"Files in test folder: {files}")

            content: bytes = await read_asset("/preview/test-folder", "cock.txt")
            print(f"File content: {content.decode('utf-8')}")

            await delete_asset("/preview/test-folder", "cock.txt")
            print("Deleted test file")

            files: list[str] = await list_assets("/preview/test-folder")
            print(f"Files after deletion: {files}")

        except Exception as e:
            print(f"Error during test: {str(e)}")

    asyncio.run(test_storage())
