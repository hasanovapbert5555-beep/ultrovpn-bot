import aiohttp
import json

async def create_outline_key(api_url, cert_sha256):
    async with aiohttp.ClientSession() as session:
        headers = {"cert-sha256": cert_sha256}
        async with session.post(f"{api_url}/keys", headers=headers, ssl=False) as resp:
            if resp.status != 200:
                return None, None
            data = await resp.json()
            return data.get("keyId"), data.get("accessUrl")

async def delete_outline_key(api_url, cert_sha256, key_id):
    async with aiohttp.ClientSession() as session:
        headers = {"cert-sha256": cert_sha256}
        await session.delete(f"{api_url}/keys/{key_id}", headers=headers, ssl=False)

async def get_outline_metrics(api_url, cert_sha256):
    async with aiohttp.ClientSession() as session:
        headers = {"cert-sha256": cert_sha256}
        async with session.get(f"{api_url}/metrics/transfer", headers=headers, ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()
            return None